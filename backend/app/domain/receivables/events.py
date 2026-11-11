"""Événements du module Créances (RG-T01, TR-09, module « receivables »).

Journalisés (`ShopAuditedEvent`) : créance ancienne créée (UC-CRE-02), versement enregistré
(UC-CRE-03), versement annulé (UC-CRE-08, **sensible**), mise en perte (UC-CRE-09,
**sensible**, SCN-08), créance modifiée (responsable, conditions, pièces), rappel programmé ou
modifié (UC-CRE-06), garant ajouté (UC-CRE-07).

Non journalisés (`NotAudited`) : l'ouverture, la révision et l'annulation d'une créance par
sa vente (la vente est déjà journalisée) et `ReminderDue` (alerte interne du jour, tâche
planifiée : pas une action d'utilisateur).
"""

from dataclasses import dataclass
from datetime import date

from app.domain.audit.entry import AuditRecord
from app.domain.audit.events import NotAudited
from app.domain.audit.values import AuditAction, EntityRef
from app.domain.receivables.ids import ReceivableId, ReminderId
from app.domain.shared.events import DomainEvent
from app.domain.shared.ids import UserId
from app.domain.shops.events import ShopAuditedEvent

RECEIVABLES_MODULE = "receivables"


@dataclass(frozen=True, kw_only=True)
class ReceivableAuditedEvent(ShopAuditedEvent):
    """Base abstraite des événements journalisés du module : motif en plus."""

    reason: str | None = None

    module = RECEIVABLES_MODULE

    def audit_record(self) -> AuditRecord:
        return AuditRecord(
            performer=self.performer,
            action=self.action,
            entity=self.entity,
            module=self.module,
            summary=self.summary,
            changes=self.changes,
            reason=self.reason,
            sensitive=self.sensitive,
        )


@dataclass(frozen=True, kw_only=True)
class LegacyReceivableRecorded(ReceivableAuditedEvent):
    action = AuditAction.CREATE


@dataclass(frozen=True, kw_only=True)
class ReceivableChanged(ReceivableAuditedEvent):
    action = AuditAction.UPDATE


@dataclass(frozen=True, kw_only=True)
class InstallmentRecorded(ReceivableAuditedEvent):
    action = AuditAction.CREATE


@dataclass(frozen=True, kw_only=True)
class InstallmentCancelled(ReceivableAuditedEvent):
    action = AuditAction.CANCEL
    sensitive = True


@dataclass(frozen=True, kw_only=True)
class ReceivableWrittenOff(ReceivableAuditedEvent):
    action = AuditAction.UPDATE
    sensitive = True


@dataclass(frozen=True, kw_only=True)
class ReminderScheduled(ReceivableAuditedEvent):
    action = AuditAction.CREATE


@dataclass(frozen=True, kw_only=True)
class ReminderChanged(ReceivableAuditedEvent):
    action = AuditAction.UPDATE


@dataclass(frozen=True, kw_only=True)
class GuarantorAdded(ReceivableAuditedEvent):
    action = AuditAction.CREATE


@dataclass(frozen=True, kw_only=True)
class ReceivableOpened(DomainEvent, NotAudited):
    """Créance ouverte par une vente à crédit (UC-CRE-01)."""

    receivable_id: ReceivableId


@dataclass(frozen=True, kw_only=True)
class ReminderDue(DomainEvent, NotAudited):
    """Le jour d'un rappel est venu : alerte « Rappel créance » (UC-CRE-06, REM-01)."""

    receivable_id: ReceivableId
    reminder_id: ReminderId
    remind_on: date
    entity: EntityRef
    responsible_seller_id: UserId | None
    message: str
