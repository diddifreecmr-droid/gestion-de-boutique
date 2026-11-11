"""Lignes enfants d'une vente (lignes, détails vendus, paiements) ↔ objets du domaine (T16a).

Lues et réécrites **avec** la vente par `SqlSaleRepository` ; filtrées sur la boutique. Les
marges sont recopiées en colonnes pour les rapports (T19) ; la vérité reste le domaine.
"""

from decimal import Decimal
from typing import Any
from uuid import UUID

import sqlalchemy as sa

from app.domain.catalog.ids import ArticleId
from app.domain.sales.ids import SalePaymentId
from app.domain.sales.lines import SaleLine, SaleMode, SoldDetail
from app.domain.sales.payments import PaymentNature, SalePayment
from app.domain.sales.sale import Sale
from app.domain.sales.values import SaleKind
from app.domain.shared.money import Money
from app.domain.shared.quantity import Quantity, StockUnit
from app.domain.shops.ids import PaymentModeId
from app.infrastructure.persistence.sqlalchemy import tables_sales as t
from app.infrastructure.persistence.sqlalchemy.transaction import SqlTransaction

CHILDREN = (t.sale_line, t.sold_detail, t.sale_payment)


def _money(value: object) -> Money | None:
    return None if value is None else Money(int(str(value)))


def _amount(value: Money | None) -> int | None:
    return None if value is None else value.amount


def _children(
    transaction: SqlTransaction, table: sa.Table, shop_id: UUID, sale_id: UUID, *order: Any
) -> list[sa.RowMapping]:
    statement = (
        sa.select(table)
        .where(table.c.sale_id == sale_id, table.c.shop_id == shop_id)
        .order_by(*order)
    )
    return transaction.fetch_all(statement)


def read_children(
    transaction: SqlTransaction, shop_id: UUID, sale_id: UUID
) -> tuple[tuple[SaleLine, ...], tuple[SalePayment, ...]]:
    detail_table = t.sold_detail
    details: dict[int, list[SoldDetail]] = {}
    order = (detail_table.c.line_position, detail_table.c.position)
    for row in _children(transaction, detail_table, shop_id, sale_id, *order):
        details.setdefault(int(row["line_position"]), []).append(
            SoldDetail(
                color=row["color"],
                chassis_number=row["chassis_number"],
                engine_number=row["engine_number"],
                size=row["size"],
            )
        )
    lines = tuple(
        SaleLine(
            article_id=ArticleId(row["article_id"]),
            article_name=row["article_name_snapshot"],
            sale_mode=SaleMode(row["sale_mode"]),
            quantity=Decimal(str(row["quantity"])),
            stock_quantity=Quantity.of(
                Decimal(str(row["stock_qty"])), StockUnit(row["stock_unit"])
            ),
            unit_price=Money(int(row["unit_price"])),
            base_price=_money(row["base_price_snapshot"]),
            frozen_last_cost=_money(row["frozen_last_cost"]),
            frozen_wac=_money(row["frozen_wac"]),
            details=tuple(details.get(int(row["position"]), ())),
        )
        for row in _children(transaction, t.sale_line, shop_id, sale_id, t.sale_line.c.position)
    )
    payments = tuple(
        SalePayment(
            id=SalePaymentId(row["id"]),
            mode_id=PaymentModeId(row["mode_id"]),
            amount=Money(int(row["amount"])),
            reference=row["reference"],
        )
        for row in _children(
            transaction, t.sale_payment, shop_id, sale_id, t.sale_payment.c.position
        )
    )
    return lines, payments


def write_children(transaction: SqlTransaction, sale: Sale, *, replace: bool) -> None:
    ids = {"sale_id": sale.id.value, "shop_id": sale.shop_id.value}
    if replace:
        for table in CHILDREN:
            transaction.write(
                sa.delete(table).where(
                    table.c.sale_id == sale.id.value, table.c.shop_id == sale.shop_id.value
                )
            )
    lines = sale.content.lines
    nature = PaymentNature.CASH if sale.kind is SaleKind.CASH else PaymentNature.DEPOSIT
    rows: list[tuple[sa.Table, list[dict[str, Any]]]] = [
        (t.sale_line, [ids | _line(i, line) for i, line in enumerate(lines)]),
        (
            t.sold_detail,
            [
                ids | _detail(i, j, detail)
                for i, line in enumerate(lines)
                for j, detail in enumerate(line.details)
            ],
        ),
        (
            t.sale_payment,
            [ids | _payment(i, p, nature) for i, p in enumerate(sale.content.payments)],
        ),
    ]
    for table, values in rows:
        if values:
            transaction.write(sa.insert(table).values(values))


def _line(position: int, line: SaleLine) -> dict[str, Any]:
    return {
        "position": position,
        "article_id": line.article_id.value,
        "article_name_snapshot": line.article_name,
        "sale_mode": line.sale_mode.value,
        "quantity": line.quantity,
        "stock_unit": line.stock_quantity.unit.value,
        "stock_qty": line.stock_quantity.value,
        "base_price_snapshot": _amount(line.base_price),
        "unit_price": line.unit_price.amount,
        "line_total": line.line_total.amount,
        "frozen_last_cost": _amount(line.frozen_last_cost),
        "frozen_wac": _amount(line.frozen_wac),
        "margin": _amount(line.margin),
        "margin_wac": _amount(line.margin_wac),
    }


def _detail(line_position: int, position: int, detail: SoldDetail) -> dict[str, Any]:
    return {
        "line_position": line_position,
        "position": position,
        "color": detail.color,
        "chassis_number": detail.chassis_number,
        "chassis_key": detail.chassis_key,
        "engine_number": detail.engine_number,
        "size": detail.size,
    }


def _payment(position: int, payment: SalePayment, nature: PaymentNature) -> dict[str, Any]:
    return {
        "position": position,
        "id": payment.id.value,
        "mode_id": payment.mode_id.value,
        "amount": payment.amount.amount,
        "reference": payment.reference,
        "nature": nature.value,
    }
