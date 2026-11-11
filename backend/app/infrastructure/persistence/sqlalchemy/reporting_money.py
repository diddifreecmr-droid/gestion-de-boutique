"""Agrégats SQL de l'argent encaissé et des dépenses pour le tableau de bord (T19, RG-T21).

Index de période utilisés : `sale (shop_id, sold_on)` puis `sale_payment` par sa clé primaire,
`sale (shop_id, cancelled_at)`, `installment (shop_id, paid_on)`, `installment (shop_id,
cancelled_at)`, `sale_return (shop_id, refunded_on)`, `expense (shop_id, spent_on)`, `expense
(shop_id, cancelled_at)` (les trois derniers ajoutés par la migration `0011`). Les annulations
sont rattachées à leur journée de Douala en Python (voir `reporting_sales.py`).
"""

from collections.abc import Iterable
from datetime import date
from typing import Any

import sqlalchemy as sa

from app.application.reporting.ports import ExpenseFlow, FlowKind, MoneyFlow
from app.domain.sales.payments import PaymentNature
from app.domain.shared.business_day import business_date, period_bounds_utc
from app.domain.shared.ids import ShopId
from app.domain.shops.ids import ExpenseCategoryId, PaymentModeId
from app.infrastructure.persistence.sqlalchemy import tables_expenses as e
from app.infrastructure.persistence.sqlalchemy import tables_receivables as rc
from app.infrastructure.persistence.sqlalchemy import tables_sales as t
from app.infrastructure.persistence.sqlalchemy import tables_sales_returns as r
from app.infrastructure.persistence.sqlalchemy.columns import from_db, to_db
from app.infrastructure.persistence.sqlalchemy.reporting_sales import S, cancelled_window, total
from app.infrastructure.persistence.sqlalchemy.transaction import SqlTransaction

P = t.sale_payment.c
_PAYMENTS = t.sale.join(t.sale_payment, sa.and_(P.sale_id == S.id, P.shop_id == S.shop_id))
_NATURES = {
    PaymentNature.CASH.value: FlowKind.SALE_CASH,
    PaymentNature.DEPOSIT.value: FlowKind.SALE_DEPOSIT,
}

_N = sa.func.count().label("n")

type Sums = dict[tuple[date, Any, Any], list[int]]
"""(journée, nature, mode ou catégorie) -> [montant, nombre]."""


def _add(sums: Sums, key: tuple[date, Any, Any], amount: int, count: int) -> None:
    acc = sums.setdefault(key, [0, 0])
    acc[0] += amount
    acc[1] += count


def _window(column: sa.ColumnElement[Any], first: date, last: date) -> list[sa.ColumnElement[bool]]:
    start, end = period_bounds_utc(first, last)
    return [column >= to_db(start), column < to_db(end)]


def _bucket(sums: Sums, rows: Iterable[sa.RowMapping], kind: object, key: str, at: str) -> None:
    """Range chaque ligne (instant d'annulation `at`) dans sa journée de Douala."""
    for row in rows:
        _add(sums, (business_date(from_db(row[at])), kind, row[key]), int(row["amount"]), 1)


def _grouped(sums: Sums, rows: Iterable[sa.RowMapping], kind: object, key: str, day: str) -> None:
    """Lignes déjà sommées par SQL (colonnes `amount` et `n`)."""
    for row in rows:
        _add(sums, (row[day], kind, row[key]), int(row["amount"]), int(row["n"]))


def _ordered(sums: Sums) -> list[tuple[tuple[date, Any, Any], list[int]]]:
    return sorted(sums.items(), key=lambda item: tuple(map(str, item[0])))


def money_flows(tx: SqlTransaction, shop_id: ShopId, first: date, last: date) -> list[MoneyFlow]:
    shop = shop_id.value
    sums: Sums = {}
    amount, n = total(P.amount).label("amount"), _N
    paid = (
        sa.select(S.sold_on, P.nature, P.mode_id, amount, n)
        .select_from(_PAYMENTS)
        .where(S.shop_id == shop, S.sold_on >= first, S.sold_on <= last)
        .group_by(S.sold_on, P.nature, P.mode_id)
    )
    for row in tx.fetch_all(paid):
        key = (row["sold_on"], _NATURES[row["nature"]], row["mode_id"])
        _add(sums, key, int(row["amount"]), int(row["n"]))
    undone = sa.select(S.cancelled_at, P.mode_id, P.amount).select_from(_PAYMENTS)
    undone = undone.where(S.shop_id == shop, *cancelled_window(first, last))
    _bucket(sums, tx.fetch_all(undone), FlowKind.SALE_CANCELLED, "mode_id", "cancelled_at")
    i = rc.installment.c
    received = (
        sa.select(i.paid_on, i.mode_id, total(i.amount).label("amount"), n)
        .where(i.shop_id == shop, i.paid_on >= first, i.paid_on <= last)
        .group_by(i.paid_on, i.mode_id)
    )
    _grouped(sums, tx.fetch_all(received), FlowKind.INSTALLMENT, "mode_id", "paid_on")
    voided = sa.select(i.cancelled_at, i.mode_id, i.amount).where(
        i.shop_id == shop, *_window(i.cancelled_at, first, last)
    )
    _bucket(sums, tx.fetch_all(voided), FlowKind.INSTALLMENT_CANCELLED, "mode_id", "cancelled_at")
    c = r.sale_return.c
    refunds = (
        sa.select(c.refunded_on, c.refund_mode_id, total(c.refund_amount).label("amount"), n)
        .where(c.shop_id == shop, c.refunded_on >= first, c.refunded_on <= last)
        .where(c.refund_amount.is_not(None))
        .group_by(c.refunded_on, c.refund_mode_id)
    )
    _grouped(sums, tx.fetch_all(refunds), FlowKind.REFUND, "refund_mode_id", "refunded_on")
    return [
        MoneyFlow(day=d, kind=k, mode_id=PaymentModeId(m), amount=a, count=n)
        for (d, k, m), (a, n) in _ordered(sums)
    ]


def expense_flows(
    tx: SqlTransaction, shop_id: ShopId, first: date, last: date
) -> list[ExpenseFlow]:
    x = e.expense.c
    sums: Sums = {}
    spent = (
        sa.select(
            x.spent_on, x.category_id, total(x.amount).label("amount"), sa.func.count().label("n")
        )
        .where(x.shop_id == shop_id.value, x.spent_on >= first, x.spent_on <= last)
        .group_by(x.spent_on, x.category_id)
    )
    _grouped(sums, tx.fetch_all(spent), False, "category_id", "spent_on")
    undone = sa.select(x.cancelled_at, x.category_id, x.amount).where(
        x.shop_id == shop_id.value, *_window(x.cancelled_at, first, last)
    )
    _bucket(sums, tx.fetch_all(undone), True, "category_id", "cancelled_at")
    return [
        ExpenseFlow(day=d, category_id=ExpenseCategoryId(c), amount=a, count=n, cancelled=k)
        for (d, k, c), (a, n) in _ordered(sums)
    ]
