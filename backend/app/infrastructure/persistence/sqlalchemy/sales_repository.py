"""Adaptateur SQL des ventes (T16a) : la vente suit le gabarit `SqlRepository` (verrou optimiste
sur `sale`), puis ses lignes, détails et paiements sont réécrits (`sales_rows.py`).

Les lectures du vendeur ajoutent `seller_id = :vendeur` **à la requête** (portée OWN).
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

import sqlalchemy as sa

from app.application.sales.ports import SaleRepository
from app.domain.catalog.ids import ArticleId
from app.domain.purchasing.values import Cancellation, Capture
from app.domain.sales.ids import CustomerId, SaleId
from app.domain.sales.sale import Sale
from app.domain.sales.values import CreditTerms, SaleContent, SaleKind, SaleStatus
from app.domain.shared.business_day import period_bounds_utc
from app.domain.shared.doc_number import DocNumber, ProvisionalDocNumber
from app.domain.shared.ids import DeviceId, ShopId, UserId
from app.domain.shops.ids import LocationId
from app.infrastructure.persistence.sqlalchemy import tables_sales as t
from app.infrastructure.persistence.sqlalchemy.columns import from_db, to_db
from app.infrastructure.persistence.sqlalchemy.sales import (
    SqlChassisClaimRepository,
    SqlCustomerRepository,
)
from app.infrastructure.persistence.sqlalchemy.sales_documents import (
    SqlErrorReportRepository,
    SqlReceiptPrintRepository,
)
from app.infrastructure.persistence.sqlalchemy.sales_rows import read_children, write_children
from app.infrastructure.persistence.sqlalchemy.shops import SqlListing


class SqlSaleRepository(SqlListing[SaleId, Sale], SaleRepository):
    table = t.sale

    def _to_columns(self, aggregate: Sale) -> dict[str, Any]:
        content, capture, cancel = aggregate.content, aggregate.capture, aggregate.cancellation
        credit, provisional = aggregate.credit, aggregate.provisional_number
        return {
            "number": str(aggregate.number),
            "provisional_number": None if provisional is None else str(provisional),
            "kind": aggregate.kind.value,
            "status": aggregate.status.value,
            "location_id": aggregate.location_id.value,
            "seller_id": aggregate.seller_id.value,
            "customer_id": None if content.customer_id is None else content.customer_id.value,
            "sold_on": content.sold_on,
            "sold_at": to_db(aggregate.sold_at),
            "total": aggregate.total.amount,
            "paid": aggregate.paid.amount,
            "note": content.note,
            "reminder_on": None if credit is None else credit.reminder_on,
            "credit_terms": None if credit is None else credit.terms,
            "stock_to_verify": aggregate.stock_to_verify,
            "created_by": capture.created_by.value,
            "device_id": capture.device_id.value,
            "captured_at": to_db(capture.captured_at),
            "received_at": to_db(capture.received_at),
            "cancelled_at": None if cancel is None else to_db(cancel.at),
            "cancelled_by": None if cancel is None else cancel.by.value,
            "cancel_reason": None if cancel is None else cancel.reason,
        }

    def _from_row(self, row: sa.RowMapping) -> Sale:
        lines, payments = read_children(self._transaction, self.shop_id.value, row["id"])
        customer, provisional = row["customer_id"], row["provisional_number"]
        kind = SaleKind(row["kind"])
        cancelled = row["cancelled_at"]
        return Sale(
            id=SaleId(row["id"]),
            shop_id=ShopId(row["shop_id"]),
            number=DocNumber.parse(row["number"]),
            kind=kind,
            location_id=LocationId(row["location_id"]),
            seller_id=UserId(row["seller_id"]),
            content=SaleContent(
                sold_on=row["sold_on"],
                lines=lines,
                payments=payments,
                customer_id=None if customer is None else CustomerId(customer),
                note=row["note"],
            ),
            capture=Capture(
                created_by=UserId(row["created_by"]),
                device_id=DeviceId(row["device_id"]),
                captured_at=from_db(row["captured_at"]),
                received_at=from_db(row["received_at"]),
            ),
            credit=None
            if kind is SaleKind.CASH
            else CreditTerms(reminder_on=row["reminder_on"], terms=row["credit_terms"]),
            provisional_number=None
            if provisional is None
            else ProvisionalDocNumber.parse(provisional),
            stock_to_verify=bool(row["stock_to_verify"]),
            cancellation=None
            if cancelled is None
            else Cancellation(
                from_db(cancelled), UserId(row["cancelled_by"]), row["cancel_reason"]
            ),
            version=int(row["version"]),
        )

    def _insert(self, aggregate: Sale) -> None:
        super()._insert(aggregate)
        write_children(self._transaction, aggregate, replace=False)

    def _save(self, aggregate: Sale, *, expected_version: int) -> None:
        super()._save(aggregate, expected_version=expected_version)
        write_children(self._transaction, aggregate, replace=True)

    # ------------------------------------------------------------------ lectures
    def _recent(self, *conditions: Any, seller: UserId | None) -> list[Sale]:
        c = self.table.c
        if seller is not None:
            conditions = (*conditions, c.seller_id == seller.value)
        return self._select_all(c.sold_at.desc(), c.id.desc(), where=sa.and_(*conditions))

    def list_between(
        self, first_day: date, last_day: date, *, seller: UserId | None = None
    ) -> list[Sale]:
        c = self.table.c
        return self._recent(c.sold_on >= first_day, c.sold_on <= last_day, seller=seller)

    def cancelled_between(
        self, first_day: date, last_day: date, *, seller: UserId | None = None
    ) -> list[Sale]:
        start, end = period_bounds_utc(first_day, last_day)
        c = self.table.c
        return self._recent(c.cancelled_at >= start, c.cancelled_at < end, seller=seller)

    def find_by_reference(
        self, number: str | None, chassis: str | None, *, seller: UserId | None = None
    ) -> list[Sale]:
        c, d = self.table.c, t.sold_detail.c
        matches: list[Any] = []
        if number is not None:
            matches += [c.number == number, c.provisional_number == number]
        if chassis is not None:
            carrying = sa.select(d.sale_id).where(
                d.shop_id == self.shop_id.value, d.chassis_key == chassis
            )
            matches.append(c.id.in_(carrying))
        if not matches:
            return []
        return self._recent(sa.or_(*matches), seller=seller)

    def for_customer(self, customer_id: CustomerId, *, seller: UserId | None = None) -> list[Sale]:
        return self._recent(self.table.c.customer_id == customer_id.value, seller=seller)

    def quantities_since(self, since: datetime) -> dict[ArticleId, Decimal]:
        c, line = self.table.c, t.sale_line.c
        statement = (
            sa.select(line.article_id, sa.func.sum(line.stock_qty).label("sold"))
            .select_from(t.sale_line.join(self.table, line.sale_id == c.id))
            .where(
                c.shop_id == self.shop_id.value,
                line.shop_id == self.shop_id.value,
                c.status == SaleStatus.VALID.value,
                c.sold_at >= to_db(since),
            )
            .group_by(line.article_id)
        )
        rows = self._transaction.fetch_all(statement)
        return {ArticleId(row["article_id"]): Decimal(str(row["sold"])) for row in rows}


SQL_SALES_REPOSITORIES = (
    SqlCustomerRepository,
    SqlSaleRepository,
    SqlChassisClaimRepository,
    SqlErrorReportRepository,
    SqlReceiptPrintRepository,
)
