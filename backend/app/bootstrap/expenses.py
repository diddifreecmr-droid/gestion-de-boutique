"""Assemblage du module Dépenses (T18) : cas d'utilisation sur les unités de boutique.

Les unités de travail sont celles du noyau (journal et alertes branchés) : chaque saisie,
correction, annulation ou fusion est journalisée dans la même transaction (TR-09).
"""

from dataclasses import dataclass

from app.application.expenses.use_cases.cancel_expense import CancelExpense
from app.application.expenses.use_cases.correct_expense import CorrectExpense
from app.application.expenses.use_cases.get_expense import GetExpense
from app.application.expenses.use_cases.list_expenses import ListExpenses
from app.application.expenses.use_cases.list_tags import ListTags
from app.application.expenses.use_cases.manage_expense_categories import (
    ManageExpenseCategories,
)
from app.application.expenses.use_cases.merge_tags import MergeTags
from app.application.expenses.use_cases.record_expense import RecordExpense
from app.application.expenses.use_cases.repeat_expense import RepeatExpense
from app.application.security.policy import Policy
from app.bootstrap.identity import IdentityModule
from app.interface.http.routes.expense_components import ExpensesComponents


@dataclass(frozen=True, slots=True, kw_only=True)
class ExpensesModule:
    http: ExpensesComponents


def build_expenses(identity: IdentityModule) -> ExpensesModule:
    clock, uows = identity.clock, identity.core.shop_uow_factory
    policy = Policy(clock=clock.now)
    http = ExpensesComponents(
        record=RecordExpense(uows, policy, clock),
        correct=CorrectExpense(uows, policy, clock),
        cancel=CancelExpense(uows, policy, clock),
        get=GetExpense(uows, policy, clock),
        list=ListExpenses(uows, policy, clock),
        repeat=RepeatExpense(uows, policy, clock),
        categories=ManageExpenseCategories(uows, policy, clock),
        tags=ListTags(uows, policy),
        merge_tags=MergeTags(uows, policy, clock),
        guard=identity.auth.guard,
    )
    return ExpensesModule(http=http)
