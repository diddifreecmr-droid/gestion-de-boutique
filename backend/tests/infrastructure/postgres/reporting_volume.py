"""Volume réaliste pour expliquer les agrégats du tableau de bord (specs § 10) : une boutique avec
plusieurs années d'activité, insérée directement en SQL puis analysée (`ANALYZE`), pour que le
planificateur de PostgreSQL choisisse ses index sur de vraies statistiques."""

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

import sqlalchemy as sa

from app.domain.shared.ids import ShopId, UserId
from app.infrastructure.persistence.sqlalchemy import tables_expenses as e
from app.infrastructure.persistence.sqlalchemy import tables_receivables as rc
from app.infrastructure.persistence.sqlalchemy import tables_sales as t
from app.infrastructure.persistence.sqlalchemy import tables_sales_returns as r

ROWS = 2_000


def _id() -> UUID:
    return UserId.new().value  # identifiants UUIDv7, comme ceux de l'application


FIRST_DAY = date(2024, 1, 1)
SELLERS = [_id() for _ in range(10)]


def _day(n: int) -> date:
    return FIRST_DAY + timedelta(days=n % 1_000)


def _at(n: int) -> datetime:
    return datetime.combine(_day(n), datetime.min.time(), tzinfo=UTC) + timedelta(hours=9)


def _cancelled(n: int) -> datetime | None:
    return _at(n) + timedelta(days=3) if n % 10 == 0 else None


def _common(shop: UUID, n: int) -> dict[str, Any]:
    return {"id": _id(), "shop_id": shop, "version": 1}


def _sales(shop: UUID) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    sales, lines, payments = [], [], []
    for n in range(ROWS):
        row = _common(shop, n) | {
            "number": f"V-{n + 1:06d}", "provisional_number": None, "kind": "cash",
            "status": "cancelled" if _cancelled(n) else "valid", "location_id": _id(),
            "seller_id": SELLERS[n % 10], "customer_id": None, "sold_on": _day(n),
            "sold_at": _at(n), "total": 780_000, "paid": 780_000, "note": None,
            "reminder_on": None, "credit_terms": None, "stock_to_verify": False,
            "created_by": SELLERS[n % 10], "device_id": _id(), "captured_at": _at(n),
            "received_at": _at(n), "cancelled_at": _cancelled(n), "cancelled_by": None,
            "cancel_reason": "x" if _cancelled(n) else None,
        }  # fmt: skip
        sales.append(row)
        lines.append({
            "sale_id": row["id"], "position": 1, "shop_id": shop, "article_id": _id(),
            "article_name_snapshot": "Haojue", "sale_mode": "unit", "quantity": 1,
            "stock_unit": "unit", "stock_qty": 1, "base_price_snapshot": None,
            "unit_price": 780_000, "line_total": 780_000, "frozen_last_cost": 550_000,
            "frozen_wac": 530_000, "margin": 230_000, "margin_wac": 250_000,
        })  # fmt: skip
        payments.append({"sale_id": row["id"], "position": 1, "id": _id(), "shop_id": shop,
                         "mode_id": _id(), "amount": 780_000, "reference": None,
                         "nature": "cash"})  # fmt: skip
    return sales, lines, payments


def _returns(shop: UUID, sales: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        _common(shop, n)
        | {
            "sale_id": sales[n]["id"],
            "sale_number": sales[n]["number"],
            "kind": "return",
            "lines": [],
            "reason": "x",
            "amount": 780_000,
            "margin": 230_000,
            "margin_wac": 250_000,
            "refund_amount": 780_000,
            "refund_mode_id": _id(),
            "refunded_on": _day(n),
            "credit_reduction": 0,
            "exchange_sale_id": None,
            "returned_at": _at(n),
            "returned_on": _day(n),
            "created_by": SELLERS[0],
        }
        for n in range(ROWS)
    ]


def _receivables(shop: UUID) -> tuple[list[dict[str, Any]], ...]:
    receivables, installments, reminders = [], [], []
    for n in range(ROWS // 10):
        row = _common(shop, n) | {
            "customer_id": _id(), "origin": "legacy", "sale_id": None, "sale_number": None,
            "sale_total": None, "paid_at_sale": 0, "description": "x", "initial_amount": 10**9,
            "opened_on": _day(n), "responsible_seller_id": SELLERS[n % 10], "terms": None,
            "status": "open" if n % 3 else "settled", "attachment_ids": [],
            "written_off_on": None, "write_off_reason": None, "written_off_by": None,
            "written_off_at": None, "sale_cancelled_on": None, "sale_cancelled_at": None,
            "recorded_at": _at(n),
        }  # fmt: skip
        receivables.append(row)
        for k in range(10):
            m = n * 10 + k
            installments.append({
                "id": _id(), "receivable_id": row["id"], "shop_id": shop, "position": k,
                "number": f"R-{m + 1:06d}", "paid_on": _day(m), "amount": 50_000,
                "mode_id": _id(), "reference": None, "nature": "normal",
                "status": "cancelled" if _cancelled(m) else "valid", "to_refund": False,
                "created_by": SELLERS[0], "device_id": _id(), "captured_at": _at(m),
                "received_at": _at(m), "cancelled_at": _cancelled(m), "cancelled_by": None,
                "cancel_reason": None,
            })  # fmt: skip
            reminders.append({
                "id": _id(), "receivable_id": row["id"], "shop_id": shop, "position": k,
                "remind_on": _day(m), "note": None, "status": "done" if k % 2 else "upcoming",
                "alerted_for": None, "created_by": SELLERS[0], "created_at": _at(m),
            })  # fmt: skip
    return receivables, installments, reminders


def _others(shop: UUID) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    expenses = [
        _common(shop, n)
        | {
            "number": f"D-{n + 1:06d}",
            "spent_on": _day(n),
            "amount": 25_000,
            "category_id": _id(),
            "payment_mode_id": _id(),
            "description": None,
            "location_id": None,
            "beneficiary": None,
            "attachment_id": None,
            "status": "cancelled" if _cancelled(n) else "valid",
            "created_by": SELLERS[0],
            "device_id": _id(),
            "captured_at": _at(n),
            "received_at": _at(n),
            "cancelled_at": _cancelled(n),
            "cancelled_by": None,
            "cancel_reason": None,
        }
        for n in range(ROWS)
    ]
    requests = [
        _common(shop, n)
        | {
            "seller_id": SELLERS[n % 10],
            "article_id": _id(),
            "article_name": "Haojue",
            "location_id": _id(),
            "requested_price": 700_000,
            "min_price": 720_000,
            "status": ("pending", "accepted", "refused", "expired")[n % 4],
            "requested_at": _at(n),
            "expires_at": _at(n) + timedelta(minutes=30),
            "decided_by": None,
            "decided_at": None,
            "sale_id": None,
        }
        for n in range(ROWS)
    ]
    return expenses, requests


def seed_volume(engine: sa.Engine, shop_id: ShopId) -> None:
    shop = shop_id.value
    sales, lines, payments = _sales(shop)
    receivables, installments, reminders = _receivables(shop)
    expenses, requests = _others(shop)
    batches = [
        (t.sale, sales), (t.sale_line, lines), (t.sale_payment, payments),
        (r.sale_return, _returns(shop, sales)), (rc.receivable, receivables),
        (rc.installment, installments), (rc.receivable_reminder, reminders),
        (e.expense, expenses), (r.price_request, requests),
    ]  # fmt: skip
    with engine.begin() as connection:
        for table, rows in batches:
            connection.execute(sa.insert(table), rows)
        for table, _rows in batches:
            connection.exec_driver_sql(f"ANALYZE {table.name}")
