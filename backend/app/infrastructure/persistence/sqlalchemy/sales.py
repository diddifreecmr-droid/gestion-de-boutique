"""Adaptateurs SQL du module Ventes (T16a) : clients et châssis réservés.

La vente et ses enfants sont dans `sales_repository.py`, signalements et impressions dans
`sales_documents.py`. La portée « ses clients » du vendeur
est une sous-requête (`created_by = :vendeur OR id IN (ventes du vendeur)`), dans la requête.
"""

from typing import Any

import sqlalchemy as sa

from app.application.sales.ports import (
    ChassisClaimRepository,
    CustomerQuery,
    CustomerRepository,
)
from app.domain.catalog.ids import AttachmentId
from app.domain.identity.phone import PhoneNumber
from app.domain.sales.chassis import ChassisClaim
from app.domain.sales.customer import Customer, CustomerDetails
from app.domain.sales.ids import ChassisClaimId, CustomerId, SaleId
from app.domain.shared.ids import ShopId, UserId
from app.domain.shared.money import Money
from app.infrastructure.persistence.sqlalchemy import tables_sales as t
from app.infrastructure.persistence.sqlalchemy.columns import from_db, to_db
from app.infrastructure.persistence.sqlalchemy.shops import SqlListing


def _optional(value: Any) -> Any:
    return None if value is None else value.value


class SqlCustomerRepository(SqlListing[CustomerId, Customer], CustomerRepository):
    table = t.customer

    def _to_columns(self, aggregate: Customer) -> dict[str, Any]:
        d = aggregate.details
        return {
            "name": d.name,
            "phone": d.phone.e164,
            "kind": d.kind.value,
            "city": d.city,
            "address": d.address,
            "id_doc_type": None if d.id_doc_type is None else d.id_doc_type.value,
            "id_doc_number": d.id_doc_number,
            "id_doc_photo_id": _optional(d.id_doc_photo_id),
            "credit_limit": None if d.credit_limit is None else d.credit_limit.amount,
            "note": d.note,
            "search_key": aggregate.search_key,
            "sort_key": aggregate.sort_key,
            "created_by": aggregate.created_by.value,
            "created_at": to_db(aggregate.created_at),
        }

    def _from_row(self, row: sa.RowMapping) -> Customer:
        photo, limit = row["id_doc_photo_id"], row["credit_limit"]
        details = CustomerDetails(
            name=row["name"],
            phone=PhoneNumber(row["phone"]),
            kind=row["kind"],
            city=row["city"],
            address=row["address"],
            id_doc_type=row["id_doc_type"],
            id_doc_number=row["id_doc_number"],
            id_doc_photo_id=None if photo is None else AttachmentId(photo),
            credit_limit=None if limit is None else Money(int(limit)),
            note=row["note"],
        )
        return Customer(
            id=CustomerId(row["id"]),
            shop_id=ShopId(row["shop_id"]),
            details=details,
            created_by=UserId(row["created_by"]),
            created_at=from_db(row["created_at"]),
            version=int(row["version"]),
        )

    def _seller_scope(self, seller: UserId) -> sa.ColumnElement[bool]:
        sales = t.sale.c
        theirs = sa.select(sales.customer_id).where(
            sales.shop_id == self.shop_id.value,
            sales.seller_id == seller.value,
            sales.customer_id.is_not(None),
        )
        return sa.or_(self.table.c.created_by == seller.value, self.table.c.id.in_(theirs))

    def find_by_phone(self, phone: PhoneNumber) -> Customer | None:
        found = self._select_all(self.table.c.id, where=self.table.c.phone == phone.e164)
        return found[0] if found else None

    def visible_to(self, customer_id: CustomerId, seller: UserId) -> bool:
        statement = sa.select(self.table.c.id).where(
            self._own(customer_id), self._seller_scope(seller)
        )
        return self._transaction.exists(statement)

    def search(self, query: CustomerQuery) -> list[Customer]:
        c = self.table.c
        conditions: list[sa.ColumnElement[bool]] = []
        text = query.folded
        if text is not None:
            conditions.append(c.search_key.like(f"%{text}%"))
        if query.seller is not None:
            conditions.append(self._seller_scope(query.seller))
        where = sa.and_(*conditions) if conditions else None
        return self._select_all(c.sort_key, c.id, where=where)


class SqlChassisClaimRepository(SqlListing[ChassisClaimId, ChassisClaim], ChassisClaimRepository):
    table = t.sold_chassis

    def _to_columns(self, aggregate: ChassisClaim) -> dict[str, Any]:
        return {
            "chassis_key": aggregate.key,
            "chassis_value": aggregate.value,
            "active_key": aggregate.active_key,
            "sale_id": aggregate.sale_id.value,
            "sale_number": aggregate.sale_number,
        }

    def _from_row(self, row: sa.RowMapping) -> ChassisClaim:
        return ChassisClaim(
            id=ChassisClaimId(row["id"]),
            shop_id=ShopId(row["shop_id"]),
            key=row["chassis_key"],
            value=row["chassis_value"],
            sale_id=SaleId(row["sale_id"]),
            sale_number=row["sale_number"],
            active=row["active_key"] is not None,
            version=int(row["version"]),
        )

    def find_active(self, key: str) -> ChassisClaim | None:
        found = self._select_all(self.table.c.id, where=self.table.c.active_key == key)
        return found[0] if found else None

    def for_sale(self, sale_id: SaleId) -> list[ChassisClaim]:
        return self._select_all(self.table.c.id, where=self.table.c.sale_id == sale_id.value)
