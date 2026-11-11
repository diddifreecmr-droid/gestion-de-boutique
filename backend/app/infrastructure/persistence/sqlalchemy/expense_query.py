"""Port de requête SQL des dépenses (UC-DEP-03, TR-21) : liste paginée et totaux.

Requêtes portables : filtres paramétrés, `IN (sous-requête)` pour le tag, `GROUP BY` pour la
répartition par catégorie (dépenses valides seulement, RG-T03). Toujours filtrées sur la
boutique du port (specs § 8.3), y compris la sous-requête des tags.
"""

from typing import Any

import sqlalchemy as sa

from app.application.expenses.ports import (
    CategoryTotal,
    ExpenseFilters,
    ExpenseQuery,
    ExpenseTotals,
    position,
)
from app.application.ports.pagination import Page, PageRequest, page_of
from app.domain.expenses.expense import Expense, ExpenseStatus
from app.domain.shops.ids import ExpenseCategoryId
from app.infrastructure.persistence.sqlalchemy import tables_expenses as t
from app.infrastructure.persistence.sqlalchemy.columns import before_cursor
from app.infrastructure.persistence.sqlalchemy.expenses import SQL_EXPENSE_REPOSITORIES, hydrate
from app.infrastructure.persistence.sqlalchemy.shop_store import SqlShopStore


class SqlExpenseQuery(SqlShopStore, ExpenseQuery):
    table = t.expense

    def _where(self, filters: ExpenseFilters) -> list[sa.ColumnElement[bool]]:
        c = self.table.c
        conditions: list[sa.ColumnElement[bool]] = [
            self._own_shop(),
            c.spent_on >= filters.first_day,
            c.spent_on <= filters.last_day,
        ]
        equal: list[tuple[Any, Any]] = [
            (c.category_id, filters.category_id),
            (c.location_id, filters.location_id),
            (c.created_by, filters.created_by),
            (c.payment_mode_id, filters.payment_mode_id),
        ]
        conditions += [column == value.value for column, value in equal if value is not None]
        if filters.tag_id is not None:
            links = t.expense_tag.c
            tagged = sa.select(links.expense_id).where(
                links.shop_id == self.shop_id.value, links.tag_id == filters.tag_id.value
            )
            conditions.append(c.id.in_(tagged))
        return conditions

    def search(self, filters: ExpenseFilters, page: PageRequest) -> Page[Expense]:
        c = self.table.c
        statement = sa.select(self.table).where(*self._where(filters))
        if page.after is not None:
            statement = statement.where(before_cursor(c.received_at, c.id, page.after))
        statement = statement.order_by(c.received_at.desc(), c.id.desc()).limit(page.limit + 1)
        rows = self._transaction.fetch_all(statement)
        return page_of(hydrate(self._transaction, self.shop_id, rows), page, position)

    def totals(self, filters: ExpenseFilters) -> ExpenseTotals:
        c = self.table.c
        amount = sa.func.sum(c.amount)
        statement = (
            sa.select(c.category_id, amount.label("amount"), sa.func.count().label("count"))
            .where(*self._where(filters), c.status == ExpenseStatus.VALID.value)
            .group_by(c.category_id)
            .order_by(amount.desc(), c.category_id)
        )
        by_category = tuple(
            CategoryTotal(
                ExpenseCategoryId(row["category_id"]), int(row["amount"]), int(row["count"])
            )
            for row in self._transaction.fetch_all(statement)
        )
        return ExpenseTotals(
            amount=sum(total.amount for total in by_category),
            count=sum(total.count for total in by_category),
            by_category=by_category,
        )


SQL_EXPENSE_ADAPTERS = (*SQL_EXPENSE_REPOSITORIES, SqlExpenseQuery)
"""Adaptateurs SQL du module Dépenses, à inscrire dans les registres (`SQL_REPOSITORIES`)."""
