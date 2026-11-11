"""Assemblage du module Créances (T17) : créances, versements, rappels, garants, relevé.

- Le handler `ReceivableSync` (créance tenue par sa vente, même transaction) et la règle
  d'alerte « Rappel créance » sont branchés par le noyau (`bootstrap/core.py`).
- Le dû client servi aux Ventes (`ReceivableCustomerDebt`) est câblé par `bootstrap/sales.py`.
- `dispatch_reminders` : tâche planifiée idempotente (TR-19), à appeler par le futur worker
  pour chaque boutique (`execute(shop_id, today)`).
"""

from dataclasses import dataclass

from app.application.receivables.reminders import DispatchDueReminders
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
from app.application.security.policy import Policy
from app.bootstrap.identity import IdentityModule
from app.interface.http.routes.receivables_components import ReceivablesComponents


@dataclass(frozen=True, slots=True, kw_only=True)
class ReceivablesModule:
    http: ReceivablesComponents
    dispatch_reminders: DispatchDueReminders


def build_receivables(identity: IdentityModule) -> ReceivablesModule:
    uows, clock = identity.core.shop_uow_factory, identity.clock
    policy = Policy(clock=clock.now)
    http = ReceivablesComponents(
        list=ListReceivables(uows, policy, clock),
        get=GetReceivable(uows, policy, clock),
        record_legacy=RecordLegacyReceivable(uows, policy, clock),
        change=ChangeReceivable(uows, policy, clock),
        record_installment=RecordInstallment(uows, policy, clock),
        cancel_installment=CancelInstallment(uows, policy, clock),
        receipt=GetInstallmentReceipt(uows, policy),
        write_off=WriteOffReceivable(uows, policy, clock),
        schedule_reminder=ScheduleReminder(uows, policy, clock),
        change_reminder=ChangeReminder(uows, policy, clock),
        add_guarantor=AddGuarantor(uows, policy, clock),
        statement=CustomerStatement(uows, policy),
        guard=identity.auth.guard,
    )
    return ReceivablesModule(http=http, dispatch_reminders=DispatchDueReminders(uows, clock))
