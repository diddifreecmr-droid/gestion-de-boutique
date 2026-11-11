"""Agrégat `SyncOperation` : trace d'une saisie hors connexion reçue par `POST /sync` (TR-11).

Une ligne par `op_id` (identifiant client UUIDv7, specs § 6.5) : c'est la clé d'**idempotence**
de la synchronisation. Un `op_id` déjà traité renvoie le résultat gardé ici, sans rien rejouer
(ni second document, ni seconde alerte).

- `ACCEPTED` : le document a été créé (`entity_id`, numéro définitif `number`) ; le numéro
  provisoire reste lié au définitif (RG-T06) ;
- `REJECTED` : refus métier gardé avec son code et son message (la saisie reste visible sur
  l'appareil, RG-T23) ; la création émet `OfflineEntryRefused` (journal + alerte).

Le statut « duplicate » n'est pas stocké : c'est la réponse à un `op_id` déjà `ACCEPTED`.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Self
from uuid import UUID

from app.domain.audit.values import EntityRef, Performer
from app.domain.shared.business_day import require_aware
from app.domain.shared.events import EventCollector
from app.domain.shared.ids import DeviceId, EntityId, ShopId, UserId
from app.domain.sync.events import OfflineEntryRefused

OP_TYPE_MAX = 32
ERROR_MESSAGE_MAX = 500


class SyncOperationId(EntityId):
    """`op_id` fourni par l'appareil (UUIDv7)."""

    __slots__ = ()


class SyncStatus(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True, kw_only=True)
class SyncOrigin:
    """Qui a saisi, sur quel appareil, quand (heure de l'appareil, H12) et quand reçu."""

    created_by: UserId
    device_id: DeviceId
    captured_at: datetime
    received_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "captured_at", require_aware(self.captured_at))
        object.__setattr__(self, "received_at", require_aware(self.received_at))


@dataclass(eq=False, kw_only=True)
class SyncOperation:
    id: SyncOperationId
    shop_id: ShopId
    op_type: str
    origin: SyncOrigin
    status: SyncStatus
    provisional_number: str | None = None
    entity_id: UUID | None = None
    number: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    version: int = 0
    events: EventCollector = field(default_factory=EventCollector, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.id, SyncOperationId) or not isinstance(self.status, SyncStatus):
            msg = "SyncOperation exige un SyncOperationId et un SyncStatus"
            raise TypeError(msg)
        if not self.op_type or len(self.op_type) > OP_TYPE_MAX:
            msg = f"Type d'opération vide ou de plus de {OP_TYPE_MAX} caractères"
            raise ValueError(msg)
        accepted = self.status is SyncStatus.ACCEPTED
        if accepted and (self.entity_id is None or self.number is None):
            msg = "Une opération acceptée porte le document créé et son numéro définitif"
            raise ValueError(msg)
        if not accepted and not (self.error_code and self.error_message):
            msg = "Une opération refusée porte son code et son motif"
            raise ValueError(msg)

    @classmethod
    def accepted(
        cls,
        op_id: SyncOperationId,
        shop_id: ShopId,
        *,
        op_type: str,
        origin: SyncOrigin,
        provisional_number: str | None,
        entity_id: UUID,
        number: str,
    ) -> Self:
        return cls(
            id=op_id,
            shop_id=shop_id,
            op_type=op_type,
            origin=origin,
            status=SyncStatus.ACCEPTED,
            provisional_number=provisional_number,
            entity_id=entity_id,
            number=number,
        )

    @classmethod
    def rejected(
        cls,
        op_id: SyncOperationId,
        shop_id: ShopId,
        *,
        op_type: str,
        origin: SyncOrigin,
        provisional_number: str | None,
        error_code: str,
        error_message: str,
        performer: Performer,
    ) -> Self:
        """Refus gardé ; émet `OfflineEntryRefused` (journal, alerte « Saisie refusée »)."""
        operation = cls(
            id=op_id,
            shop_id=shop_id,
            op_type=op_type[:OP_TYPE_MAX],
            origin=origin,
            status=SyncStatus.REJECTED,
            provisional_number=provisional_number,
            error_code=error_code,
            error_message=error_message[:ERROR_MESSAGE_MAX],
        )
        label = provisional_number or operation.op_type
        operation.events.record(
            OfflineEntryRefused(
                shop_id=shop_id,
                occurred_at=origin.received_at,
                performer=performer,
                entity=EntityRef("sync_operation", op_id.value, provisional_number),
                summary=f"Saisie hors connexion refusée : {label} ({error_code})"[:500],
                author_id=origin.created_by,
                op_type=operation.op_type,
                error_code=error_code,
                provisional_number=provisional_number,
            )
        )
        return operation
