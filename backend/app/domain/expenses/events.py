"""Événements du module Dépenses, tous journalisés (RG-T01, TR-09, module « expenses »).

Ils reprennent la base `ShopAuditedEvent` (auteur, élément, résumé, avant/après) et y ajoutent
le **motif** (annulation, UC-DEP-04) et l'instant de **capture** sur l'appareil (RG-T04) : le
journal sait ainsi qu'une saisie est arrivée en retard. Une annulation est toujours « sensible »
(RG-T03 ; aussi imposé par `SENSITIVE_ACTIONS`).
"""

from dataclasses import dataclass
from datetime import datetime

from app.domain.audit.entry import AuditRecord
from app.domain.audit.values import AuditAction
from app.domain.shops.events import ShopAuditedEvent

EXPENSES_MODULE = "expenses"


@dataclass(frozen=True, kw_only=True)
class ExpenseAuditedEvent(ShopAuditedEvent):
    """Base abstraite des événements du module : motif et capture en plus."""

    reason: str | None = None
    captured_at: datetime | None = None

    module = EXPENSES_MODULE

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
class ExpenseRecorded(ExpenseAuditedEvent):
    action = AuditAction.CREATE


@dataclass(frozen=True, kw_only=True)
class ExpenseCorrected(ExpenseAuditedEvent):
    action = AuditAction.UPDATE


@dataclass(frozen=True, kw_only=True)
class ExpenseCancelled(ExpenseAuditedEvent):
    action = AuditAction.CANCEL
    sensitive = True


@dataclass(frozen=True, kw_only=True)
class TagCreated(ExpenseAuditedEvent):
    action = AuditAction.CREATE


@dataclass(frozen=True, kw_only=True)
class TagMerged(ExpenseAuditedEvent):
    action = AuditAction.UPDATE


@dataclass(frozen=True, kw_only=True)
class ExpenseCategoryCreated(ExpenseAuditedEvent):
    action = AuditAction.CONFIGURE


@dataclass(frozen=True, kw_only=True)
class ExpenseCategoryChanged(ExpenseAuditedEvent):
    action = AuditAction.CONFIGURE
