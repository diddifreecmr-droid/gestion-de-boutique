"""Port `AuditLog` : journal **en ajout seul** de la boutique (TR-09, RG-J01, specs § 8.4).

Le port n'hérite pas de `Repository` : il n'a **ni** `update` **ni** suppression, par aucun
moyen (vérifié par `tests/contracts/test_audit_contract.py`). Il s'obtient comme un dépôt,
lié à la boutique et à la transaction : `AuditLog.within(uow)`. Une entrée écrite dans une
transaction annulée disparaît avec elle (même transaction que l'action, D7).

Lecture (UC-JRN-01 à 03) : `search` filtre et pagine du plus récent au plus ancien, sur
`(received_at, id)` — l'index `(shop_id, received_at DESC)` de specs § 10.
"""

from abc import abstractmethod
from collections.abc import Set
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from app.application.ports.errors import IsolationViolation
from app.application.ports.pagination import Cursor, Page, PageRequest
from app.application.ports.shop_bound import ShopBoundPort
from app.domain.audit.entry import AuditEntry
from app.domain.audit.values import AuditAction
from app.domain.shared.business_day import require_aware
from app.domain.shared.ids import UserId


@dataclass(frozen=True, slots=True, kw_only=True)
class AuditQuery:
    """Filtres combinés par ET ; un filtre vide (`None`, ensemble vide) ne restreint rien.

    `since`/`until` : bornes UTC `[since, until)` sur l'heure **de l'action** (`captured_at`),
    celle qu'affiche le journal (« 10/11 14 h 32 »).
    """

    since: datetime | None = None
    until: datetime | None = None
    user_id: UserId | None = None
    actions: Set[AuditAction] = field(default_factory=frozenset)
    modules: Set[str] = field(default_factory=frozenset)
    entity_type: str | None = None
    entity_id: UUID | None = None

    def __post_init__(self) -> None:
        for name in ("since", "until"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, require_aware(value))
        object.__setattr__(self, "actions", frozenset(self.actions))
        object.__setattr__(self, "modules", frozenset(self.modules))
        if self.entity_id is not None and self.entity_type is None:
            msg = "Un filtre par identifiant d'élément exige son type"
            raise ValueError(msg)

    def matches(self, entry: AuditEntry) -> bool:
        """Sémantique de référence des filtres (adaptateur mémoire, tests)."""
        return (
            (self.since is None or entry.captured_at >= self.since)
            and (self.until is None or entry.captured_at < self.until)
            and (self.user_id is None or entry.performer.user_id == self.user_id)
            and (not self.actions or entry.action in self.actions)
            and (not self.modules or entry.module in self.modules)
            and (self.entity_type is None or entry.entity.type == self.entity_type)
            and (self.entity_id is None or entry.entity.id == self.entity_id)
        )


def position(entry: AuditEntry) -> Cursor:
    """Position d'une entrée dans l'ordre du journal (plus récente d'abord)."""
    return Cursor(entry.received_at, entry.id.value)


class AuditLog(ShopBoundPort):
    """Journal de la boutique de l'unité de travail : `append` et lectures, rien d'autre."""

    def append(self, entry: AuditEntry) -> None:
        """Inscrit `entry` ; `Duplicate` si son identifiant est pris.

        Une entrée d'une autre boutique est un bogue : `IsolationViolation`.
        """
        if not isinstance(entry, AuditEntry):
            msg = f"AuditLog.append attend une AuditEntry, reçu {type(entry).__name__}"
            raise TypeError(msg)
        if entry.shop_id != self.shop_id:
            msg = "Entrée de journal d'une autre boutique transmise à AuditLog"
            raise IsolationViolation(msg)
        self._append(entry)

    @abstractmethod
    def search(self, query: AuditQuery, page: PageRequest) -> Page[AuditEntry]:
        """Entrées de la boutique qui satisfont `query`, plus récentes d'abord."""

    @abstractmethod
    def _append(self, entry: AuditEntry) -> None:
        """Primitive d'adaptateur : écrit l'entrée (déjà contrôlée) dans la transaction."""
