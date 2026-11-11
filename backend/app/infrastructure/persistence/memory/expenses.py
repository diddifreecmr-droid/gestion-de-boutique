"""Adaptateurs mémoire du module Dépenses : dépôts (dépenses, tags) et port de requête (T18).

Le port de requête lit la **même table** que le dépôt des dépenses, dans la transaction de
l'unité de travail (il voit donc ses propres écritures, comme en SQL).
"""

import copy
from collections import defaultdict
from typing import cast

from app.application.expenses.ports import (
    CategoryTotal,
    ExpenseFilters,
    ExpenseQuery,
    ExpenseRepository,
    ExpenseTotals,
    TagRepository,
    position,
)
from app.application.ports.pagination import Page, PageRequest, paginate
from app.domain.expenses.expense import Expense, ExpenseStatus
from app.domain.expenses.ids import ExpenseId, TagId
from app.domain.expenses.tag import Tag
from app.domain.shops.ids import ExpenseCategoryId
from app.infrastructure.persistence.memory.shop_store import MemoryShopStore
from app.infrastructure.persistence.memory.shops import _Listing

EXPENSES_TABLE = "expenses"


class MemoryExpenseRepository(_Listing[ExpenseId, Expense], ExpenseRepository):
    table = EXPENSES_TABLE

    def list_with_tag(self, tag_id: TagId) -> list[Expense]:
        found = self._sorted(key=position)
        return [expense for expense in found if tag_id in expense.details.tag_ids]


class MemoryTagRepository(_Listing[TagId, Tag], TagRepository):
    table = "tags"

    def find_by_key(self, key: str) -> Tag | None:
        found = [tag for tag in self._sorted(key=lambda tag: tag.id) if tag.name_key == key]
        return found[0] if found else None

    def list_all(self) -> list[Tag]:
        return self._sorted(key=lambda tag: (tag.name_key, tag.id))


def matches(expense: Expense, filters: ExpenseFilters) -> bool:
    details = expense.details
    wanted = (
        (filters.category_id, details.category_id),
        (filters.location_id, details.location_id),
        (filters.created_by, expense.capture.created_by),
        (filters.payment_mode_id, details.payment_mode_id),
    )
    return (
        filters.first_day <= details.spent_on <= filters.last_day
        and all(value is None or value == actual for value, actual in wanted)
        and (filters.tag_id is None or filters.tag_id in details.tag_ids)
    )


class MemoryExpenseQuery(MemoryShopStore, ExpenseQuery):
    table = EXPENSES_TABLE

    def _matching(self, filters: ExpenseFilters) -> list[Expense]:
        # Les lignes de cette table ne sont écrites que par `MemoryExpenseRepository`.
        rows = self._transaction.rows(self.table)
        expenses = [cast(Expense, copy.deepcopy(row.payload)) for row in rows]
        return [expense for expense in expenses if matches(expense, filters)]

    def search(self, filters: ExpenseFilters, page: PageRequest) -> Page[Expense]:
        ordered = sorted(self._matching(filters), key=position, reverse=True)
        return paginate(ordered, page, position)

    def totals(self, filters: ExpenseFilters) -> ExpenseTotals:
        amounts: dict[ExpenseCategoryId, list[int]] = defaultdict(list)
        for expense in self._matching(filters):
            if expense.status is ExpenseStatus.VALID:
                amounts[expense.details.category_id].append(expense.details.amount)
        by_category = sorted(
            (CategoryTotal(cat, sum(values), len(values)) for cat, values in amounts.items()),
            key=lambda total: (-total.amount, total.category_id),
        )
        return ExpenseTotals(
            amount=sum(total.amount for total in by_category),
            count=sum(total.count for total in by_category),
            by_category=tuple(by_category),
        )


EXPENSE_REPOSITORIES = (MemoryExpenseRepository, MemoryTagRepository, MemoryExpenseQuery)
