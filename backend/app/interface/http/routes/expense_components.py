"""Cas d'utilisation du module Dépenses, assemblés par la composition root (T18)."""

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
from app.interface.http.security import AuthGuard


@dataclass(frozen=True, slots=True, kw_only=True)
class ExpensesComponents:
    record: RecordExpense
    correct: CorrectExpense
    cancel: CancelExpense
    get: GetExpense
    list: ListExpenses
    repeat: RepeatExpense
    categories: ManageExpenseCategories
    tags: ListTags
    merge_tags: MergeTags
    guard: AuthGuard
