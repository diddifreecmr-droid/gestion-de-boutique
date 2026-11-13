"""Adaptateurs mémoire du module Ventes (T16a) : clients, ventes, châssis, signalements, reçus.

Même sémantique que l'adaptateur SQL (`tests/contracts/test_sales_contract.py`) : unicités
`customer_phone`, `sale_number`, `sold_chassis_active` (clé `NULL` une fois libérée),
`receipt_print_sequence` ; portée « ses clients / ses ventes » appliquée dans la lecture.
"""

from datetime import date, datetime
from decimal import Decimal

from app.application.sales.ports import (
    ChassisClaimRepository,
    CustomerQuery,
    CustomerRepository,
    ErrorReportRepository,
    ReceiptPrintRepository,
    SaleRepository,
    position,
)
from app.domain.catalog.ids import ArticleId
from app.domain.identity.phone import PhoneNumber
from app.domain.sales.chassis import ChassisClaim
from app.domain.sales.customer import Customer
from app.domain.sales.error_report import ErrorReport
from app.domain.sales.ids import ChassisClaimId, CustomerId, ErrorReportId, ReceiptPrintId, SaleId
from app.domain.sales.receipt_print import ReceiptPrint
from app.domain.sales.sale import Sale
from app.domain.sales.values import SaleStatus
from app.domain.shared.business_day import business_date
from app.domain.shared.ids import UserId
from app.infrastructure.persistence.memory.shops import _Listing


def _of(sales: list[Sale], seller: UserId | None) -> list[Sale]:
    return [sale for sale in sales if seller is None or sale.seller_id == seller]


class MemorySaleRepository(_Listing[SaleId, Sale], SaleRepository):
    table = "sales"

    def _recent(self, seller: UserId | None) -> list[Sale]:
        found = self._sorted(key=position)
        found.reverse()
        return _of(found, seller)

    def list_between(
        self, first_day: date, last_day: date, *, seller: UserId | None = None
    ) -> list[Sale]:
        return [s for s in self._recent(seller) if first_day <= s.content.sold_on <= last_day]

    def cancelled_between(
        self, first_day: date, last_day: date, *, seller: UserId | None = None
    ) -> list[Sale]:
        return [
            s
            for s in self._recent(seller)
            if s.cancellation is not None
            and first_day <= business_date(s.cancellation.at) <= last_day
        ]

    def find_by_reference(
        self, number: str | None, chassis: str | None, *, seller: UserId | None = None
    ) -> list[Sale]:
        def hit(sale: Sale) -> bool:
            numbers = {str(sale.number)}
            if sale.provisional_number is not None:
                numbers.add(str(sale.provisional_number))
            keys = {d.chassis_key for line in sale.content.lines for d in line.details}
            return (number is not None and number in numbers) or (
                chassis is not None and chassis in keys
            )

        return [sale for sale in self._recent(seller) if hit(sale)]

    def for_customer(self, customer_id: CustomerId, *, seller: UserId | None = None) -> list[Sale]:
        return [s for s in self._recent(seller) if s.content.customer_id == customer_id]

    def quantities_since(self, since: datetime) -> dict[ArticleId, Decimal]:
        sold: dict[ArticleId, Decimal] = {}
        for sale in self._recent(None):
            if sale.status is not SaleStatus.VALID or sale.sold_at < since:
                continue
            for line in sale.content.lines:
                sold[line.article_id] = sold.get(line.article_id, Decimal(0)) + (
                    line.stock_quantity.value
                )
        return sold


class MemoryCustomerRepository(_Listing[CustomerId, Customer], CustomerRepository):
    table = "customers"

    def find_by_phone(self, phone: PhoneNumber) -> Customer | None:
        found = [c for c in self._sorted(key=lambda c: c.id) if c.unique_phone == phone.e164]
        return found[0] if found else None

    def visible_to(self, customer_id: CustomerId, seller: UserId) -> bool:
        customer = self._load(customer_id)
        if customer is None:
            return False
        if customer.created_by == seller:
            return True
        sales = MemorySaleRepository(self.shop_id, self._tracker, self._transaction)
        return bool(sales.for_customer(customer_id, seller=seller))

    def search(self, query: CustomerQuery) -> list[Customer]:
        found = self._sorted(key=lambda c: (c.sort_key, c.id))
        matching = [c for c in found if not c.released and query.matches(c)]
        if query.seller is None:
            return matching
        return [c for c in matching if self.visible_to(c.id, query.seller)]


class MemoryChassisClaimRepository(_Listing[ChassisClaimId, ChassisClaim], ChassisClaimRepository):
    table = "sold_chassis"

    def find_active(self, key: str) -> ChassisClaim | None:
        found = [c for c in self._sorted(key=lambda c: c.id) if c.active_key == key]
        return found[0] if found else None

    def for_sale(self, sale_id: SaleId) -> list[ChassisClaim]:
        return [c for c in self._sorted(key=lambda c: c.id) if c.sale_id == sale_id]


class MemoryErrorReportRepository(_Listing[ErrorReportId, ErrorReport], ErrorReportRepository):
    table = "sale_error_reports"

    def for_sale(self, sale_id: SaleId) -> list[ErrorReport]:
        ordered = self._sorted(key=lambda r: (r.reported_at, r.id))
        return [report for report in ordered if report.sale_id == sale_id]


class MemoryReceiptPrintRepository(_Listing[ReceiptPrintId, ReceiptPrint], ReceiptPrintRepository):
    table = "receipt_prints"

    def count_for(self, sale_id: SaleId) -> int:
        return len([p for p in self._sorted(key=lambda p: p.id) if p.sale_id == sale_id])


MEMORY_SALES_REPOSITORIES = (
    MemoryCustomerRepository,
    MemorySaleRepository,
    MemoryChassisClaimRepository,
    MemoryErrorReportRepository,
    MemoryReceiptPrintRepository,
)
