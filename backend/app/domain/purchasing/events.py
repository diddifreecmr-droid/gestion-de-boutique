"""Événements du module Achats, tous journalisés (RG-T01, TR-09, module « purchases »).

Base `ShopAuditedEvent` + motif et instant de capture (comme les dépenses). Correction et
annulation d'un achat sont « sensibles » : elles rejouent le stock et le CMP (UC-ACH-03/04).
"""

from dataclasses import dataclass
from datetime import datetime

from app.domain.audit.entry import AuditRecord
from app.domain.audit.values import AuditAction
from app.domain.shops.events import ShopAuditedEvent

PURCHASES_MODULE = "purchases"


@dataclass(frozen=True, kw_only=True)
class PurchasingAuditedEvent(ShopAuditedEvent):
    """Base abstraite des événements du module : motif et capture en plus."""

    reason: str | None = None
    captured_at: datetime | None = None

    module = PURCHASES_MODULE

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
            captured_at=self.captured_at,
        )


@dataclass(frozen=True, kw_only=True)
class SupplierCreated(PurchasingAuditedEvent):
    action = AuditAction.CREATE


@dataclass(frozen=True, kw_only=True)
class SupplierChanged(PurchasingAuditedEvent):
    action = AuditAction.UPDATE


@dataclass(frozen=True, kw_only=True)
class PurchaseRecorded(PurchasingAuditedEvent):
    action = AuditAction.CREATE


@dataclass(frozen=True, kw_only=True)
class PurchaseCorrected(PurchasingAuditedEvent):
    action = AuditAction.UPDATE
    sensitive = True


@dataclass(frozen=True, kw_only=True)
class PurchaseCancelled(PurchasingAuditedEvent):
    action = AuditAction.CANCEL
    sensitive = True


@dataclass(frozen=True, kw_only=True)
class SupplierPaymentRecorded(PurchasingAuditedEvent):
    action = AuditAction.CREATE
