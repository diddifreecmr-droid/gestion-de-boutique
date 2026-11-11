"""Adaptateurs SQL du module Achats (T15) : fournisseurs, achats (et leurs enfants).

L'achat suit le gabarit `SqlRepository` (verrou optimiste sur la ligne `purchase`), puis ses
lignes, frais et paiements sont réécrits dans la même transaction (`purchasing_rows.py`).
"""

from datetime import date
from typing import Any

import sqlalchemy as sa

from app.application.purchasing.ports import PurchaseRepository, SupplierRepository
from app.domain.catalog.ids import AttachmentId
from app.domain.purchasing.ids import PurchaseId, SupplierId
from app.domain.purchasing.purchase import Purchase
from app.domain.purchasing.supplier import Supplier, SupplierDetails
from app.domain.purchasing.values import Cancellation, Capture, PurchaseDetails
from app.domain.shared.doc_number import DocNumber
from app.domain.shared.ids import DeviceId, EntityId, ShopId, UserId
from app.domain.shops.ids import LocationId
from app.infrastructure.persistence.sqlalchemy import tables_purchasing as t
from app.infrastructure.persistence.sqlalchemy.columns import from_db, to_db
from app.infrastructure.persistence.sqlalchemy.purchasing_rows import read_children, write_children
from app.infrastructure.persistence.sqlalchemy.shops import SqlListing


def _uuid(value: EntityId | None) -> Any:
    return None if value is None else value.value


class SqlSupplierRepository(SqlListing[SupplierId, Supplier], SupplierRepository):
    table = t.supplier

    def _to_columns(self, aggregate: Supplier) -> dict[str, Any]:
        details = aggregate.details
        return {
            "name": details.name,
            "name_key": aggregate.name_key,
            "phone": details.phone,
            "city": details.city,
            "country": details.country,
            "note": details.note,
            "active": details.active,
            "created_at": to_db(aggregate.created_at),
        }

    def _from_row(self, row: sa.RowMapping) -> Supplier:
        details = SupplierDetails(
            name=row["name"],
            phone=row["phone"],
            city=row["city"],
            country=row["country"],
            note=row["note"],
            active=bool(row["active"]),
        )
        return Supplier(
            id=SupplierId(row["id"]),
            shop_id=ShopId(row["shop_id"]),
            details=details,
            created_at=from_db(row["created_at"]),
            version=int(row["version"]),
        )

    def list_all(self) -> list[Supplier]:
        return self._select_all(self.table.c.name_key, self.table.c.id)


class SqlPurchaseRepository(SqlListing[PurchaseId, Purchase], PurchaseRepository):
    table = t.purchase

    def _to_columns(self, aggregate: Purchase) -> dict[str, Any]:
        details, capture, cancel = aggregate.details, aggregate.capture, aggregate.cancellation
        return {
            "number": str(aggregate.number),
            "supplier_id": _uuid(details.supplier_id),
            "purchase_date": details.purchase_date,
            "entry_at": to_db(aggregate.entry_instant),
            "location_id": details.location_id.value,
            "invoice_ref": details.invoice_ref,
            "invoice_photo_id": _uuid(details.invoice_photo_id),
            "note": details.note,
            "status": aggregate.status.value,
            "merchandise_total": aggregate.merchandise_total.amount,
            "fees_total": aggregate.fees_total.amount,
            "total": aggregate.total.amount,
            "created_by": capture.created_by.value,
            "device_id": capture.device_id.value,
            "captured_at": to_db(capture.captured_at),
            "received_at": to_db(capture.received_at),
            "cancelled_at": None if cancel is None else to_db(cancel.at),
            "cancelled_by": None if cancel is None else cancel.by.value,
            "cancel_reason": None if cancel is None else cancel.reason,
        }

    def _from_row(self, row: sa.RowMapping) -> Purchase:
        costed, fees, payments = read_children(self._transaction, self.shop_id.value, row["id"])
        supplier, photo = row["supplier_id"], row["invoice_photo_id"]
        details = PurchaseDetails(
            purchase_date=row["purchase_date"],
            location_id=LocationId(row["location_id"]),
            lines=tuple(line.line for line in costed),
            fees=fees,
            supplier_id=None if supplier is None else SupplierId(supplier),
            invoice_ref=row["invoice_ref"],
            invoice_photo_id=None if photo is None else AttachmentId(photo),
            note=row["note"],
        )
        cancelled = row["cancelled_at"]
        cancellation = (
            None
            if cancelled is None
            else Cancellation(from_db(cancelled), UserId(row["cancelled_by"]), row["cancel_reason"])
        )
        return Purchase(
            id=PurchaseId(row["id"]),
            shop_id=ShopId(row["shop_id"]),
            number=DocNumber.parse(row["number"]),
            details=details,
            costed=costed,
            capture=Capture(
                created_by=UserId(row["created_by"]),
                device_id=DeviceId(row["device_id"]),
                captured_at=from_db(row["captured_at"]),
                received_at=from_db(row["received_at"]),
            ),
            payments=payments,
            cancellation=cancellation,
            version=int(row["version"]),
        )

    def _insert(self, aggregate: Purchase) -> None:
        super()._insert(aggregate)
        write_children(self._transaction, aggregate, replace=False)

    def _save(self, aggregate: Purchase, *, expected_version: int) -> None:
        super()._save(aggregate, expected_version=expected_version)
        write_children(self._transaction, aggregate, replace=True)

    def list_between(self, first_day: date, last_day: date) -> list[Purchase]:
        c = self.table.c
        where = sa.and_(c.purchase_date >= first_day, c.purchase_date <= last_day)
        return self._select_all(c.entry_at.desc(), c.id.desc(), where=where)


SQL_PURCHASING_REPOSITORIES = (SqlSupplierRepository, SqlPurchaseRepository)
