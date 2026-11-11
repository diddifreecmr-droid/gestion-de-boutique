"""Événements journalisés du module Ventes (RG-T01, TR-09, module « sales »).

Base `ShopAuditedEvent` + motif et instant de capture. Sont **sensibles** (pastille du journal,
UC-JRN-01) : la vente sous le prix minimum par le propriétaire (ERR-PRM-03), toute modification
de prix d'une vente (UC-VEN-07) et l'annulation (UC-VEN-08). Les événements destinés aux
Créances (T17) sont dans `receivable_events.py` (non journalisés : la vente l'est déjà).
"""

from dataclasses import dataclass
from datetime import datetime

from app.domain.audit.entry import AuditRecord
from app.domain.audit.values import AuditAction
from app.domain.shops.events import ShopAuditedEvent

SALES_MODULE = "sales"


@dataclass(frozen=True, kw_only=True)
class SalesAuditedEvent(ShopAuditedEvent):
    """Base abstraite des événements du module : motif et capture en plus."""

    reason: str | None = None
    captured_at: datetime | None = None

    module = SALES_MODULE

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
class CustomerCreated(SalesAuditedEvent):
    action = AuditAction.CREATE


@dataclass(frozen=True, kw_only=True)
class CustomerChanged(SalesAuditedEvent):
    action = AuditAction.UPDATE


@dataclass(frozen=True, kw_only=True)
class SaleRecorded(SalesAuditedEvent):
    action = AuditAction.CREATE


@dataclass(frozen=True, kw_only=True)
class SaleRecordedBelowMinimum(SaleRecorded):
    """Vente du propriétaire sous le prix minimum (ERR-PRM-03) : même action, sensible."""

    sensitive = True


@dataclass(frozen=True, kw_only=True)
class SaleModified(SalesAuditedEvent):
    action = AuditAction.UPDATE


@dataclass(frozen=True, kw_only=True)
class SalePriceModified(SaleModified):
    """Modification qui touche un prix vendu (UC-VEN-07) : sensible."""

    sensitive = True


@dataclass(frozen=True, kw_only=True)
class SaleCancelled(SalesAuditedEvent):
    action = AuditAction.CANCEL
    sensitive = True


@dataclass(frozen=True, kw_only=True)
class ErrorReported(SalesAuditedEvent):
    """Signalement d'un vendeur (UC-VEN-06) ; déclenche l'alerte « Erreur signalée »."""

    action = AuditAction.CREATE
    sale_number: str


@dataclass(frozen=True, kw_only=True)
class ErrorReportAnswered(SalesAuditedEvent):
    action = AuditAction.UPDATE


@dataclass(frozen=True, kw_only=True)
class ReceiptPrinted(SalesAuditedEvent):
    """Impression ou partage d'un reçu (RG-T01 « impression »), duplicata compris."""

    action = AuditAction.PRINT
