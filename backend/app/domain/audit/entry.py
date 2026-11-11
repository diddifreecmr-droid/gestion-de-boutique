"""Entrée du journal d'actions (CDC § 16.1, RG-T04, RG-J01 ; specs § 5.2 `AUDIT_ENTRY`).

- `AuditRecord` : ce qu'un événement **déclare** de lui-même (auteur, action, élément,
  changements, motif) ; il ignore l'heure d'arrivée et l'identifiant de l'entrée.
- `AuditEntry` : l'entrée inscrite, **immuable** (dataclass gelée, aucun mutateur). Le port
  `AuditLog` ne l'expose qu'en ajout et en lecture : rien ne la modifie ni ne l'efface.

Pastille « sensible » (UC-JRN-01) : déclarée par l'événement (modification de prix, vente sous
le minimum, ajustement, changement de droits), toujours vraie pour une annulation, et vraie
pour une saisie arrivée plus de `LATE_ARRIVAL` après sa capture (saisie hors connexion).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.domain.audit.values import (
    SENSITIVE_ACTIONS,
    AuditAction,
    EntityRef,
    FieldChange,
    Performer,
    require_code,
    require_text,
)
from app.domain.shared.business_day import require_aware
from app.domain.shared.ids import EntityId, ShopId

LATE_ARRIVAL = timedelta(minutes=15)
"""Écart capture → réception au-delà duquel une saisie est « arrivée en retard »."""


class AuditEntryId(EntityId):
    """Entrée du journal."""

    __slots__ = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class AuditRecord:
    """Déclaration d'une action à journaliser ; `captured_at` absent = instant de l'événement."""

    performer: Performer
    action: AuditAction
    entity: EntityRef
    module: str
    summary: str
    changes: Sequence[FieldChange] = ()
    reason: str | None = None
    sensitive: bool = False
    captured_at: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.performer, Performer) or not isinstance(self.entity, EntityRef):
            msg = "AuditRecord exige un Performer et un EntityRef"
            raise TypeError(msg)
        if not isinstance(self.action, AuditAction):
            msg = f"Action de journal inconnue : {self.action!r}"
            raise TypeError(msg)
        require_code(self.module, "AuditRecord.module")
        require_text(self.summary, "AuditRecord.summary")
        require_text(self.reason, "AuditRecord.reason", optional=True)
        changes = tuple(self.changes)
        if not all(isinstance(change, FieldChange) for change in changes):
            msg = "AuditRecord.changes n'accepte que des FieldChange"
            raise TypeError(msg)
        object.__setattr__(self, "changes", changes)
        if self.captured_at is not None:
            object.__setattr__(self, "captured_at", require_aware(self.captured_at))


@dataclass(frozen=True, slots=True, kw_only=True)
class AuditEntry:
    """Ligne du journal : figée à l'écriture (RG-J01)."""

    id: AuditEntryId
    shop_id: ShopId
    performer: Performer
    action: AuditAction
    entity: EntityRef
    module: str
    summary: str
    changes: tuple[FieldChange, ...]
    reason: str | None
    sensitive: bool
    captured_at: datetime
    received_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.id, AuditEntryId) or not isinstance(self.shop_id, ShopId):
            msg = "AuditEntry exige un AuditEntryId et un ShopId"
            raise TypeError(msg)
        object.__setattr__(self, "captured_at", require_aware(self.captured_at))
        object.__setattr__(self, "received_at", require_aware(self.received_at))

    @classmethod
    def inscribe(
        cls,
        shop_id: ShopId,
        record: AuditRecord,
        *,
        received_at: datetime,
        default_captured_at: datetime,
        entry_id: AuditEntryId | None = None,
    ) -> "AuditEntry":
        """Entrée neuve pour `record`, reçue par le serveur à `received_at`."""
        captured_at = record.captured_at or require_aware(default_captured_at)
        received = require_aware(received_at)
        late = received - captured_at > LATE_ARRIVAL
        return cls(
            id=entry_id or AuditEntryId.new(),
            shop_id=shop_id,
            performer=record.performer,
            action=record.action,
            entity=record.entity,
            module=record.module,
            summary=record.summary,
            changes=tuple(record.changes),
            reason=record.reason,
            sensitive=record.sensitive or record.action in SENSITIVE_ACTIONS or late,
            captured_at=captured_at,
            received_at=received,
        )
