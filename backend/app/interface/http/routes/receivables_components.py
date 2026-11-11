"""Cas d'utilisation du module Créances, assemblés par la composition root (T17)."""

from dataclasses import dataclass

from app.application.receivables.use_cases.follow_up import (
    AddGuarantor,
    ChangeReceivable,
    ChangeReminder,
    ScheduleReminder,
)
from app.application.receivables.use_cases.installment_receipt import GetInstallmentReceipt
from app.application.receivables.use_cases.owner_actions import (
    CancelInstallment,
    WriteOffReceivable,
)
from app.application.receivables.use_cases.read_receivables import GetReceivable, ListReceivables
from app.application.receivables.use_cases.record_installment import RecordInstallment
from app.application.receivables.use_cases.record_legacy import RecordLegacyReceivable
from app.application.receivables.use_cases.statement import CustomerStatement
from app.interface.http.security import AuthGuard


@dataclass(frozen=True, slots=True, kw_only=True)
class ReceivablesComponents:
    list: ListReceivables
    get: GetReceivable
    record_legacy: RecordLegacyReceivable
    change: ChangeReceivable
    record_installment: RecordInstallment
    cancel_installment: CancelInstallment
    receipt: GetInstallmentReceipt
    write_off: WriteOffReceivable
    schedule_reminder: ScheduleReminder
    change_reminder: ChangeReminder
    add_guarantor: AddGuarantor
    statement: CustomerStatement
    guard: AuthGuard
