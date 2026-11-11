"""Contrat des demandes de prix et des retours (T16b) : aller-retour (lignes JSON, remboursement,
statut et décision), lectures (vendeur, en attente, échues, par vente, par jour), isolation.

Rejoué sur l'adaptateur mémoire, sur SQLite (`tests/infrastructure/sqlalchemy`) et sur
PostgreSQL (`--backend=postgres`).
"""

from datetime import date, timedelta

import pytest

from app.application.sales.return_ports import PriceRequestRepository, SaleReturnRepository
from app.domain.catalog.ids import ArticleId
from app.domain.sales.ids import CustomerId
from app.domain.sales.price_request import PriceRequest, PriceRequestStatus
from app.domain.sales.return_lines import AlreadyReturned, returned_line
from app.domain.sales.sale_return import Refund, SaleReturn
from app.domain.shared.errors import NotFound
from app.domain.shared.ids import ShopId, UserId
from app.domain.shared.money import Money
from app.domain.shops.ids import LocationId, PaymentModeId
from app.domain.stock.values import StockCondition
from tests.contracts.backends import ContractBackend
from tests.contracts.catalog_data import NOW
from tests.contracts.helpers import run_in_uow
from tests.contracts.sales_data import SELLER, sale


def ask(shop_id: ShopId, minutes: int = 0) -> PriceRequest:
    return PriceRequest.ask(
        shop_id,
        article=(ArticleId.new(), "Haojue HJ125-8"),
        location_id=LocationId.new(),
        requested_price=Money(700_000),
        min_price=Money(720_000),
        performer=SELLER,
        now=NOW + timedelta(minutes=minutes),
    )


def same_request(left: PriceRequest, right: PriceRequest) -> bool:
    keys = ("seller_id", "article_id", "article_name", "location_id", "requested_price")
    rest = ("min_price", "status", "requested_at", "expires_at", "decided_by", "decided_at")
    return all(getattr(left, k) == getattr(right, k) for k in (*keys, *rest, "sale_id"))


def test_price_requests_round_trip_and_readings(
    backend: ContractBackend, shop_a: ShopId, shop_b: ShopId
) -> None:
    old, fresh = ask(shop_a), ask(shop_a, minutes=20)
    other = ask(shop_a, minutes=5)
    other.seller_id = UserId.new()

    def add(uow) -> None:  # type: ignore[no-untyped-def]
        for request in (old, fresh, other):
            PriceRequestRepository.within(uow).add(request)

    run_in_uow(backend, shop_a, add)
    with backend.uow(shop_a) as uow:
        requests = PriceRequestRepository.within(uow)
        assert same_request(requests.get(old.id), old)
        assert [r.id for r in requests.for_seller(SELLER.user_id)] == [fresh.id, old.id]
        assert [r.id for r in requests.pending()] == [fresh.id, other.id, old.id]
        due = requests.due_for_expiry(NOW + timedelta(minutes=35))
        assert [r.id for r in due] == [other.id, old.id]
        stored = requests.get(fresh.id)
        stored.decide(accept=True, performer=SELLER, now=NOW + timedelta(minutes=21))
        stored.use(sale(shop_a, 1).id, NOW + timedelta(minutes=22))
        requests.update(stored)
        uow.commit()
    with backend.uow(shop_a) as uow:
        requests = PriceRequestRepository.within(uow)
        again = requests.get(fresh.id)
        assert same_request(again, stored)
        assert again.status is PriceRequestStatus.ACCEPTED
        assert again.version == 2
        assert fresh.id not in {r.id for r in requests.due_for_expiry(NOW + timedelta(hours=2))}
    with backend.uow(shop_b) as uow, pytest.raises(NotFound):
        PriceRequestRepository.within(uow).get(old.id)


def give_back(shop_id: ShopId, minutes: int, refund: bool) -> SaleReturn:
    sold = sale(shop_id, 1, customer_id=CustomerId.new())  # crédit : acompte 300 000
    lines = [
        returned_line(sold.content.lines[0], 1, 1, StockCondition.DAMAGED, AlreadyReturned()),
        returned_line(sold.content.lines[1], 2, 2, StockCondition.SELLABLE, AlreadyReturned()),
    ]
    money = Refund(amount=Money(300_000), mode_id=PaymentModeId.new(), refunded_on=NOW.date())
    return SaleReturn.record(
        sold,
        lines,
        reason="moteur bruyant",
        previous=[],
        refund=money if refund else None,
        performer=SELLER,
        now=NOW + timedelta(days=minutes),
    )


def same_return(left: SaleReturn, right: SaleReturn) -> bool:
    keys = ("sale_id", "sale_number", "kind", "lines", "reason", "returned_at", "created_by")
    rest = ("refund", "credit_reduction", "exchange_sale_id")
    return all(getattr(left, k) == getattr(right, k) for k in (*keys, *rest))


def test_sale_returns_round_trip_and_readings(
    backend: ContractBackend, shop_a: ShopId, shop_b: ShopId
) -> None:
    first, second = give_back(shop_a, 0, refund=True), give_back(shop_a, 1, refund=False)
    second.sale_id = first.sale_id

    def add(uow) -> None:  # type: ignore[no-untyped-def]
        for made in (second, first):
            SaleReturnRepository.within(uow).add(made)

    run_in_uow(backend, shop_a, add)
    with backend.uow(shop_a) as uow:
        returns = SaleReturnRepository.within(uow)
        stored = returns.get(first.id)
        assert same_return(stored, first)
        assert stored.lines[1].quantity == first.lines[1].quantity
        assert stored.margin == first.margin
        assert stored.credit_reduction == Money(506_000)
        assert [r.id for r in returns.for_sale(first.sale_id)] == [first.id, second.id]
        day = date(2026, 11, 12)
        assert [r.id for r in returns.between(day, day)] == [second.id]
        assert returns.between(date(2026, 11, 13), date(2026, 11, 30)) == []
    with backend.uow(shop_b) as uow:
        assert SaleReturnRepository.within(uow).for_sale(first.sale_id) == []
