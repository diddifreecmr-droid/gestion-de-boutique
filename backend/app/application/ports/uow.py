"""Port `UnitOfWork` : une transaction, **une boutique** (specs § 4.4, § 8.3, D7).

Cycle de vie (à usage unique) :

    with uow_factory(shop_id) as uow:
        widgets = WidgetRepository.within(uow)
        ...
        uow.commit()

- Exception dans le `with` → rollback automatique, l'exception est **relancée**.
- Sortie normale sans `commit()` : rien n'est écrit ; si des écritures attendaient →
  `UncommittedChanges` (un oubli de commit échoue bruyamment).
- `commit()` deux fois, après `rollback()`, ou hors `with` → `UnitOfWorkStateError`.

Événements : au `commit()`, ceux des agrégats écrits (`add`/`update`) sont retirés dans
l'ordre et remis à chaque handler **avant** la validation, dans la même transaction ; ceux des
handlers suivent au tour d'après (`MAX_DISPATCH_ROUNDS` au plus). Rollback : aucune remise.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from enum import Enum, auto
from types import TracebackType
from typing import Protocol, Self

from app.application.ports.aggregate import Aggregate
from app.application.ports.errors import (
    IsolationViolation,
    UncommittedChanges,
    UnitOfWorkStateError,
    UnsavedChanges,
)
from app.application.ports.event_handler import EventHandler
from app.application.ports.numbering import DocumentNumberAllocator
from app.application.ports.shop_bound import ShopBoundPort
from app.domain.shared.events import DomainEvent
from app.domain.shared.ids import ShopId

MAX_DISPATCH_ROUNDS = 16


class _State(Enum):
    NEW = auto()
    ACTIVE = auto()
    COMMITTING = auto()  # handlers en cours : écritures permises, commit/rollback interdits
    COMMITTED = auto()
    ROLLED_BACK = auto()


class UnitOfWork(ABC):
    """Gabarit commun ; un adaptateur fournit la transaction (`_begin`, `_commit`…)."""

    def __init__(self, shop_id: ShopId, handlers: Sequence[EventHandler] = ()) -> None:
        if not isinstance(shop_id, ShopId):
            msg = f"Un UnitOfWork est lié à un ShopId, reçu {type(shop_id).__name__}"
            raise TypeError(msg)
        self._shop_id = shop_id
        self._handlers = tuple(handlers)
        self._state = _State.NEW
        self._tracked: dict[int, Aggregate] = {}  # id(objet) → agrégat, ordre de première vue
        self._saved: set[int] = set()
        self._repositories: dict[type[ShopBoundPort], ShopBoundPort] = {}

    @property
    def shop_id(self) -> ShopId:
        return self._shop_id

    # ------------------------------------------------------------------ cycle de vie
    def __enter__(self) -> Self:
        if self._state is not _State.NEW:
            msg = "Un UnitOfWork ne sert qu'une fois : en créer un nouveau"
            raise UnitOfWorkStateError(msg)
        self._begin()
        self._state = _State.ACTIVE
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._state is not _State.ACTIVE:
            return  # déjà validé ou annulé ; une exception éventuelle remonte telle quelle
        if exc_type is not None:
            self._abort()
            return  # retour None : Python relance l'exception
        pending = self._has_pending_changes()
        self._abort()
        if pending:
            msg = "Sortie du UnitOfWork sans commit() : écritures annulées"
            raise UncommittedChanges(msg)

    def commit(self) -> None:
        self._require_state(_State.ACTIVE, "commit")
        self._state = _State.COMMITTING
        try:
            self._dispatch_events()
            self._commit()
        except BaseException:
            self._abort()
            raise
        self._state = _State.COMMITTED

    def rollback(self) -> None:
        self._require_state(_State.ACTIVE, "rollback")
        self._abort()

    # ------------------------------------------------------------------ accès
    def repository_for(self, port: type[ShopBoundPort]) -> ShopBoundPort:
        """Préférer `Port.within(uow)`. Une instance par port (dépôt ou ajout seul) et par UoW."""
        self._require_open("repository_for")
        repository = self._repositories.get(port)
        if repository is None:
            repository = self._build_repository(port)
            self._repositories[port] = repository
        return repository

    @property
    def numbering(self) -> DocumentNumberAllocator:
        self._require_open("numbering")
        return self._numbering()

    def track(self, aggregate: Aggregate, *, saved: bool) -> None:
        """Appelé par les dépôts : mémorise les agrégats dont les événements seront remis."""
        self._require_open("track")
        self._tracked.setdefault(id(aggregate), aggregate)
        if saved:
            self._saved.add(id(aggregate))

    # ------------------------------------------------------------------ interne
    def _dispatch_events(self) -> None:
        for _ in range(MAX_DISPATCH_ROUNDS):
            events = self._pull_events()
            if not events:
                return
            for event in events:
                if event.shop_id != self._shop_id:
                    msg = f"Événement {type(event).__name__} d'une autre boutique"
                    raise IsolationViolation(msg)
                for handler in self._handlers:
                    handler.handle(event, self)
        msg = f"Événements encore produits après {MAX_DISPATCH_ROUNDS} tours : cascade sans fin"
        raise RuntimeError(msg)

    def _pull_events(self) -> list[DomainEvent]:
        events: list[DomainEvent] = []
        for key, aggregate in list(self._tracked.items()):
            if not len(aggregate.events):
                continue
            if key not in self._saved:
                msg = f"{type(aggregate).__name__} {aggregate.id} modifié sans update()"
                raise UnsavedChanges(msg)
            events.extend(aggregate.events.pull())
        return events

    def _abort(self) -> None:
        self._state = _State.ROLLED_BACK
        self._rollback()

    def _require_state(self, expected: _State, action: str) -> None:
        if self._state is not expected:
            msg = f"{action}() impossible : unité de travail à l'état {self._state.name}"
            raise UnitOfWorkStateError(msg)

    def _require_open(self, action: str) -> None:
        if self._state not in (_State.ACTIVE, _State.COMMITTING):
            msg = f"{action} hors transaction : unité de travail à l'état {self._state.name}"
            raise UnitOfWorkStateError(msg)

    # ------------------------------------------------------------------ primitives d'adaptateur
    @abstractmethod
    def _begin(self) -> None:
        """Ouvre la transaction."""

    @abstractmethod
    def _commit(self) -> None:
        """Valide tout ou rien ; peut lever `VersionConflict`/`Duplicate` (rien n'est écrit)."""

    @abstractmethod
    def _rollback(self) -> None:
        """Annule toutes les écritures et numéros de la transaction."""

    @abstractmethod
    def _has_pending_changes(self) -> bool:
        """Vrai si une écriture ou un numéro attend la validation."""

    @abstractmethod
    def _build_repository(self, port: type[ShopBoundPort]) -> ShopBoundPort:
        """Adaptateur de `port`, lié à cette transaction et à `shop_id` ; `LookupError` sinon."""

    @abstractmethod
    def _numbering(self) -> DocumentNumberAllocator:
        """Distributeur de numéros lié à cette transaction."""


class UnitOfWorkFactory(Protocol):
    """Fabrique injectée par la composition root : une unité de travail neuve par appel."""

    def __call__(self, shop_id: ShopId) -> UnitOfWork: ...
