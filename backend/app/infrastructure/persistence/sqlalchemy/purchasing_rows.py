"""Lignes enfants d'un achat (lignes chiffrées, frais, paiements) ↔ objets du domaine (T15).

Lues et réécrites **avec** l'achat par `SqlPurchaseRepository` ; filtrées sur la boutique.
"""

from decimal import Decimal
from typing import Any
from uuid import UUID

import sqlalchemy as sa

from app.domain.catalog.ids import ArticleId
from app.domain.purchasing.ids import SupplierPaymentId
from app.domain.purchasing.lines import CostedLine, FeeKind, PurchaseFee, PurchaseLine
from app.domain.purchasing.payments import SupplierPayment
from app.domain.purchasing.purchase import Purchase
from app.domain.purchasing.units import EntryUnit
from app.domain.shared.ids import UserId
from app.domain.shared.money import Money
from app.domain.shared.quantity import Quantity, StockUnit
from app.domain.shops.ids import PaymentModeId
from app.infrastructure.persistence.sqlalchemy import tables_purchasing as t
from app.infrastructure.persistence.sqlalchemy.columns import from_db, to_db
from app.infrastructure.persistence.sqlalchemy.transaction import SqlTransaction

CHILDREN = (t.purchase_line, t.purchase_fee, t.supplier_payment)


def _children(
    transaction: SqlTransaction, table: sa.Table, shop_id: UUID, purchase_id: UUID
) -> list[sa.RowMapping]:
    statement = (
        sa.select(table)
        .where(table.c.purchase_id == purchase_id, table.c.shop_id == shop_id)
        .order_by(table.c.position)
    )
    return transaction.fetch_all(statement)


def read_children(
    transaction: SqlTransaction, shop_id: UUID, purchase_id: UUID
) -> tuple[tuple[CostedLine, ...], tuple[PurchaseFee, ...], tuple[SupplierPayment, ...]]:
    lines = tuple(
        CostedLine(
            line=PurchaseLine(
                article_id=ArticleId(row["article_id"]),
                quantity=Decimal(str(row["entered_qty"])),
                unit=EntryUnit(row["entered_unit"]),
                unit_price=Money(int(row["unit_price"])),
            ),
            stock_quantity=Quantity.of(
                Decimal(str(row["stock_qty"])), StockUnit(row["stock_unit"])
            ),
            total=Money(int(row["line_total"])),
            fee_share=Money(int(row["fee_share"])),
            unit_cost=Money(int(row["final_unit_cost"])),
        )
        for row in _children(transaction, t.purchase_line, shop_id, purchase_id)
    )
    fees = tuple(
        PurchaseFee(kind=FeeKind(row["kind"]), amount=Money(int(row["amount"])), label=row["label"])
        for row in _children(transaction, t.purchase_fee, shop_id, purchase_id)
    )
    payments = tuple(
        SupplierPayment(
            id=SupplierPaymentId(row["id"]),
            paid_on=row["paid_on"],
            amount=Money(int(row["amount"])),
            mode_id=PaymentModeId(row["mode_id"]),
            recorded_at=from_db(row["recorded_at"]),
            recorded_by=UserId(row["recorded_by"]),
            reference=row["reference"],
        )
        for row in _children(transaction, t.supplier_payment, shop_id, purchase_id)
    )
    return lines, fees, payments


def write_children(transaction: SqlTransaction, purchase: Purchase, *, replace: bool) -> None:
    ids = {"purchase_id": purchase.id.value, "shop_id": purchase.shop_id.value}
    if replace:
        for table in CHILDREN:
            transaction.write(
                sa.delete(table).where(
                    table.c.purchase_id == purchase.id.value,
                    table.c.shop_id == purchase.shop_id.value,
                )
            )
    rows: list[tuple[sa.Table, list[dict[str, Any]]]] = [
        (t.purchase_line, [ids | _line(i, c) for i, c in enumerate(purchase.costed)]),
        (t.purchase_fee, [ids | _fee(i, f) for i, f in enumerate(purchase.details.fees)]),
        (t.supplier_payment, [ids | _payment(i, p) for i, p in enumerate(purchase.payments)]),
    ]
    for table, values in rows:
        if values:
            transaction.write(sa.insert(table).values(values))


def _line(position: int, costed: CostedLine) -> dict[str, Any]:
    line = costed.line
    return {
        "position": position,
        "article_id": line.article_id.value,
        "entered_qty": line.quantity,
        "entered_unit": line.unit.value,
        "stock_unit": costed.stock_quantity.unit.value,
        "stock_qty": costed.stock_quantity.value,
        "unit_price": line.unit_price.amount,
        "line_total": costed.total.amount,
        "fee_share": costed.fee_share.amount,
        "final_unit_cost": costed.unit_cost.amount,
    }


def _fee(position: int, fee: PurchaseFee) -> dict[str, Any]:
    return {
        "position": position,
        "kind": fee.kind.value,
        "label": fee.label,
        "amount": fee.amount.amount,
    }


def _payment(position: int, payment: SupplierPayment) -> dict[str, Any]:
    return {
        "position": position,
        "id": payment.id.value,
        "paid_on": payment.paid_on,
        "amount": payment.amount.amount,
        "mode_id": payment.mode_id.value,
        "reference": payment.reference,
        "recorded_at": to_db(payment.recorded_at),
        "recorded_by": payment.recorded_by.value,
    }
