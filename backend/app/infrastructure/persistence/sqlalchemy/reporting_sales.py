"""Agrégats SQL des ventes, annulations et retours pour le tableau de bord (T19, specs § 10).

Chaque requête est bornée par la boutique et par la période sur une colonne indexée :
`sale (shop_id, sold_on)` (ou `(shop_id, seller_id, sold_on)` pour un vendeur), `sale
(shop_id, cancelled_at)`, `sale_return (shop_id, returned_on)`. Les lignes se joignent par leur
clé primaire `(sale_id, position)`. Les sommes par **jour d'annulation** (instant UTC → journée de
Douala) sont faites en Python : SQL portable (PostgreSQL et SQLite), peu de lignes concernées.
"""

from collections import defaultdict
from datetime import date
from typing import Any

import sqlalchemy as sa

from app.application.reporting.ports import ReturnsDay, SalesDay
from app.domain.shared.business_day import business_date, period_bounds_utc
from app.domain.shared.ids import ShopId, UserId
from app.infrastructure.persistence.sqlalchemy import tables_sales as t
from app.infrastructure.persistence.sqlalchemy import tables_sales_returns as r
from app.infrastructure.persistence.sqlalchemy.columns import from_db, to_db
from app.infrastructure.persistence.sqlalchemy.transaction import SqlTransaction

S, L = t.sale.c, t.sale_line.c
_LINES = t.sale.join(t.sale_line, sa.and_(L.sale_id == S.id, L.shop_id == S.shop_id))


def null_count(column: sa.ColumnElement[Any]) -> sa.ColumnElement[Any]:
    return sa.func.coalesce(sa.func.sum(sa.case((column.is_(None), 1), else_=0)), 0)


def total(column: sa.ColumnElement[Any]) -> sa.ColumnElement[Any]:
    return sa.func.coalesce(sa.func.sum(column), 0)


def sale_scope(shop_id: ShopId, seller: UserId | None) -> list[sa.ColumnElement[bool]]:
    scope = [S.shop_id == shop_id.value]
    return scope if seller is None else [*scope, S.seller_id == seller.value]


def cancelled_window(first_day: date, last_day: date) -> list[sa.ColumnElement[bool]]:
    start, end = period_bounds_utc(first_day, last_day)
    return [S.cancelled_at >= to_db(start), S.cancelled_at < to_db(end)]


def sales_by_day(
    tx: SqlTransaction, shop_id: ShopId, first: date, last: date, seller: UserId | None
) -> list[SalesDay]:
    where = [*sale_scope(shop_id, seller), S.sold_on >= first, S.sold_on <= last]
    heads = sa.select(S.sold_on, sa.func.count().label("n"), total(S.total).label("total"))
    lines = sa.select(
        S.sold_on,
        total(L.margin).label("margin"),
        total(L.margin_wac).label("margin_wac"),
        null_count(L.margin).label("without_cost"),
        null_count(L.margin_wac).label("without_wac"),
    ).select_from(_LINES)
    counted = {row["sold_on"]: row for row in tx.fetch_all(heads.where(*where).group_by(S.sold_on))}
    margins = {row["sold_on"]: row for row in tx.fetch_all(lines.where(*where).group_by(S.sold_on))}
    return [
        SalesDay(
            day=day,
            count=int(head["n"]),
            total=int(head["total"]),
            margin=int(margins[day]["margin"]),
            margin_wac=int(margins[day]["margin_wac"]),
            without_cost=int(margins[day]["without_cost"]),
            without_wac=int(margins[day]["without_wac"]),
        )
        for day, head in sorted(counted.items())
    ]


def cancelled_by_day(
    tx: SqlTransaction, shop_id: ShopId, first: date, last: date, seller: UserId | None
) -> list[SalesDay]:
    where = [*sale_scope(shop_id, seller), *cancelled_window(first, last)]
    days: dict[date, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in tx.fetch_all(sa.select(S.cancelled_at, S.total).where(*where)):
        day = days[business_date(from_db(row["cancelled_at"]))]
        day["count"] += 1
        day["total"] += int(row["total"])
    lines = sa.select(S.cancelled_at, L.margin, L.margin_wac).select_from(_LINES)
    for row in tx.fetch_all(lines.where(*where)):
        day = days[business_date(from_db(row["cancelled_at"]))]
        for name, key in (("margin", "without_cost"), ("margin_wac", "without_wac")):
            if row[name] is None:
                day[key] += 1
            else:
                day[name] += int(row[name])
    return [SalesDay(day=day, **sums) for day, sums in sorted(days.items())]


def returns_by_day(
    tx: SqlTransaction, shop_id: ShopId, first: date, last: date, seller: UserId | None
) -> list[ReturnsDay]:
    c = r.sale_return.c
    statement = sa.select(
        c.returned_on,
        sa.func.count().label("n"),
        total(c.amount).label("amount"),
        total(c.margin).label("margin"),
        total(c.margin_wac).label("margin_wac"),
        null_count(c.margin).label("without_cost"),
    ).where(c.shop_id == shop_id.value, c.returned_on >= first, c.returned_on <= last)
    if seller is not None:
        sold_by = sa.select(S.id).where(*sale_scope(shop_id, seller), S.id == c.sale_id)
        statement = statement.where(sold_by.exists())
    rows = tx.fetch_all(statement.group_by(c.returned_on).order_by(c.returned_on))
    return [
        ReturnsDay(
            day=row["returned_on"],
            count=int(row["n"]),
            amount=int(row["amount"]),
            margin=int(row["margin"]),
            margin_wac=int(row["margin_wac"]),
            without_cost=int(row["without_cost"]),
        )
        for row in rows
    ]
