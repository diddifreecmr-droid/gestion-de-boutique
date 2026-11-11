"""`IdentityUnitOfWork` : transaction de **portée plateforme** (`User`, `DeviceSession`,
`MerchantAccount`), qui peut **joindre** des unités de travail de boutique (T10).

Voir `ports.py` pour la raison d'être (le `UnitOfWork` de T05 est lié à une boutique). Cycle de
vie identique à T05, à usage unique : exception dans le `with` → rollback ; sortie sans
`commit()` avec des écritures → `UncommittedChanges` ; au `commit()`, les événements des
agrégats écrits sont remis aux handlers **avant** la validation (lu, porteur d'événements et
non réécrit → `UnsavedChanges`).

**Transaction commune (T10).** `join_shop(shop_id)` rend une unité de travail de boutique
**jointe** : mêmes dépôts et handlers (journal, alertes) que d'habitude, mais **la même
transaction**. Son `commit()` remet ses événements à ses handlers sans rien valider ; seule
l'unité plateforme valide (ou annule) le tout. Une exception dans une unité jointe condamne la
transaction entière. Ouvrir une boutique (compte + propriétaire + boutique) et inscrire un
événement de l'identité au journal des boutiques de l'utilisateur sont ainsi atomiques.

    with platform_uow_factory() as uow:
        uow.users.add(owner)
        with uow.join_shop(shop_id) as shop_uow:
            MembershipRepository.within(shop_uow).add(membership)
            shop_uow.commit()          # handlers de boutique, rien n'est encore validé
        uow.commit()                   # tout est validé ensemble
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from enum import Enum, auto
from types import TracebackType
from typing import Protocol, Self

from app.application.identity.ports import IdentityEventHandler
from app.application.identity.repositories import (
    DeviceSessionRepository,
    MerchantAccountRepository,
    PlatformAggregate,
    UserRepository,
)
from app.application.ports.errors import UncommittedChanges, UnitOfWorkStateError, UnsavedChanges
from app.application.ports.uow import UnitOfWork
from app.domain.identity.events import IdentityEvent
from app.domain.shared.ids import ShopId

MAX_DISPATCH_ROUNDS = 16


class _State(Enum):
    NEW = auto()
    ACTIVE = auto()
    COMMITTING = auto()
    COMMITTED = auto()
    ROLLED_BACK = auto()


class IdentityUnitOfWork(ABC):
    """Gabarit commun ; un adaptateur fournit la transaction et les dépôts."""

    def __init__(self, handlers: Sequence[IdentityEventHandler] = ()) -> None:
        self._handlers = tuple(handlers)
        self._state = _State.NEW
        self._tracked: dict[int, PlatformAggregate] = {}
        self._saved: set[int] = set()

    def __enter__(self) -> Self:
        if self._state is not _State.NEW:
            msg = "Un IdentityUnitOfWork ne sert qu'une fois : en créer un nouveau"
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
            return
        if exc_type is not None:
            self._abort()
            return
        pending = self._has_pending_changes()
        self._abort()
        if pending:
            msg = "Sortie de l'IdentityUnitOfWork sans commit() : écritures annulées"
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

    @property
    def users(self) -> UserRepository:
        self._require_open("users")
        return self._users()

    @property
    def sessions(self) -> DeviceSessionRepository:
        self._require_open("sessions")
        return self._sessions()

    @property
    def merchants(self) -> MerchantAccountRepository:
        self._require_open("merchants")
        return self._merchants()

    def join_shop(self, shop_id: ShopId) -> UnitOfWork:
        """Unité de travail de boutique dans **cette** transaction (voir l'en-tête du module)."""
        self._require_open("join_shop")
        return self._join_shop(shop_id)

    def track(self, aggregate: PlatformAggregate, *, saved: bool) -> None:
        """Appelé par les dépôts : mémorise les agrégats dont les événements seront remis."""
        self._require_open("track")
        self._tracked.setdefault(id(aggregate), aggregate)
        if saved:
            self._saved.add(id(aggregate))

    def _dispatch_events(self) -> None:
        for _ in range(MAX_DISPATCH_ROUNDS):
            events = self._pull_events()
            if not events:
                return
            for event in events:
                for handler in self._handlers:
                    handler.handle(event, self)
        msg = f"Événements encore produits après {MAX_DISPATCH_ROUNDS} tours : cascade sans fin"
        raise RuntimeError(msg)

    def _pull_events(self) -> list[IdentityEvent]:
        events: list[IdentityEvent] = []
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

    @abstractmethod
    def _begin(self) -> None: ...

    @abstractmethod
    def _commit(self) -> None: ...  # tout ou rien ; `VersionConflict`/`Duplicate` possibles

    @abstractmethod
    def _rollback(self) -> None: ...

    @abstractmethod
    def _has_pending_changes(self) -> bool: ...

    # Dépôts liés à cette transaction (une instance par unité de travail).
    @abstractmethod
    def _users(self) -> UserRepository: ...

    @abstractmethod
    def _sessions(self) -> DeviceSessionRepository: ...

    @abstractmethod
    def _merchants(self) -> MerchantAccountRepository: ...

    @abstractmethod
    def _join_shop(self, shop_id: ShopId) -> UnitOfWork:
        """Unité de boutique neuve sur la transaction de celle-ci ; `LookupError` si impossible."""


class IdentityUnitOfWorkFactory(Protocol):
    """Fabrique injectée par la composition root : une unité de travail neuve par appel."""

    def __call__(self) -> IdentityUnitOfWork: ...
