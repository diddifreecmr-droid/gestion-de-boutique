"""Adaptateurs SQL des signalements d'erreur (UC-VEN-06) et des impressions de reçus (UC-VEN-04)."""

from typing import Any

import sqlalchemy as sa

from app.application.sales.ports import ErrorReportRepository, ReceiptPrintRepository
from app.domain.sales.error_report import ErrorReport
from app.domain.sales.ids import ErrorReportId, ReceiptPrintId, SaleId
from app.domain.sales.receipt_print import ReceiptPrint
from app.domain.shared.ids import ShopId, UserId
from app.infrastructure.persistence.sqlalchemy import tables_sales as t
from app.infrastructure.persistence.sqlalchemy.columns import from_db, from_db_optional, to_db
from app.infrastructure.persistence.sqlalchemy.shops import SqlListing


def _optional(value: Any) -> Any:
    return None if value is None else value.value


class SqlErrorReportRepository(SqlListing[ErrorReportId, ErrorReport], ErrorReportRepository):
    table = t.sale_error_report

    def _to_columns(self, aggregate: ErrorReport) -> dict[str, Any]:
        replied = aggregate.replied_at
        return {
            "sale_id": aggregate.sale_id.value,
            "sale_number": aggregate.sale_number,
            "reported_by": aggregate.reported_by.value,
            "description": aggregate.description,
            "reported_at": to_db(aggregate.reported_at),
            "status": aggregate.status.value,
            "owner_reply": aggregate.owner_reply,
            "replied_at": None if replied is None else to_db(replied),
            "replied_by": _optional(aggregate.replied_by),
        }

    def _from_row(self, row: sa.RowMapping) -> ErrorReport:
        by = row["replied_by"]
        return ErrorReport(
            id=ErrorReportId(row["id"]),
            shop_id=ShopId(row["shop_id"]),
            sale_id=SaleId(row["sale_id"]),
            sale_number=row["sale_number"],
            reported_by=UserId(row["reported_by"]),
            description=row["description"],
            reported_at=from_db(row["reported_at"]),
            status=row["status"],
            owner_reply=row["owner_reply"],
            replied_at=from_db_optional(row["replied_at"]),
            replied_by=None if by is None else UserId(by),
            version=int(row["version"]),
        )

    def for_sale(self, sale_id: SaleId) -> list[ErrorReport]:
        c = self.table.c
        return self._select_all(c.reported_at, c.id, where=c.sale_id == sale_id.value)


class SqlReceiptPrintRepository(SqlListing[ReceiptPrintId, ReceiptPrint], ReceiptPrintRepository):
    table = t.receipt_print

    def _to_columns(self, aggregate: ReceiptPrint) -> dict[str, Any]:
        return {
            "sale_id": aggregate.sale_id.value,
            "sequence": aggregate.sequence,
            "printed_at": to_db(aggregate.printed_at),
            "printed_by": aggregate.printed_by.value,
        }

    def _from_row(self, row: sa.RowMapping) -> ReceiptPrint:
        return ReceiptPrint(
            id=ReceiptPrintId(row["id"]),
            shop_id=ShopId(row["shop_id"]),
            sale_id=SaleId(row["sale_id"]),
            sequence=int(row["sequence"]),
            printed_at=from_db(row["printed_at"]),
            printed_by=UserId(row["printed_by"]),
            version=int(row["version"]),
        )

    def count_for(self, sale_id: SaleId) -> int:
        c = self.table.c
        statement = sa.select(sa.func.count()).where(
            c.shop_id == self.shop_id.value, c.sale_id == sale_id.value
        )
        row = self._transaction.fetch_one(statement.select_from(self.table))
        return 0 if row is None else int(next(iter(row.values())))
