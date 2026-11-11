"""Adaptateurs mémoire des demandes de prix et des retours (T16b).

Même sémantique que l'adaptateur SQL (`tests/contracts/test_sales_returns_contract.py`).
"""

from datetime import date, datetime

from app.application.sales.return_ports import PriceRequestRepository, SaleReturnRepository
from app.domain.sales.ids import PriceRequestId, SaleId, SaleReturnId
from app.domain.sales.price_request import PriceRequest, PriceRequestStatus
from app.domain.sales.sale_return import SaleReturn
from app.domain.shared.ids import UserId
from app.infrastructure.persistence.memory.shops import _Listing


class MemoryPriceRequestRepository(_Listing[PriceRequestId, PriceRequest], PriceRequestRepository):
    table = "price_requests"

    def _recent(self) -> list[PriceRequest]:
        found = self._sorted(key=lambda r: (r.requested_at, r.id))
        found.reverse()
        return found

    def for_seller(self, seller: UserId) -> list[PriceRequest]:
        return [r for r in self._recent() if r.seller_id == seller]

    def pending(self) -> list[PriceRequest]:
        return [r for r in self._recent() if r.status is PriceRequestStatus.PENDING]

    def due_for_expiry(self, now: datetime) -> list[PriceRequest]:
        def open_(r: PriceRequest) -> bool:
            return r.status is PriceRequestStatus.PENDING or (
                r.status is PriceRequestStatus.ACCEPTED and r.sale_id is None
            )

        return [r for r in self._recent() if open_(r) and r.expires_at <= now]


class MemorySaleReturnRepository(_Listing[SaleReturnId, SaleReturn], SaleReturnRepository):
    table = "sale_returns"

    def _ordered(self) -> list[SaleReturn]:
        return self._sorted(key=lambda r: (r.returned_at, r.id))

    def for_sale(self, sale_id: SaleId) -> list[SaleReturn]:
        return [r for r in self._ordered() if r.sale_id == sale_id]

    def between(self, first_day: date, last_day: date) -> list[SaleReturn]:
        return [r for r in self._ordered() if first_day <= r.returned_on <= last_day]


MEMORY_SALES_RETURNS_REPOSITORIES = (MemoryPriceRequestRepository, MemorySaleReturnRepository)
