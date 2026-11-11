"""Domaine T16b : lignes rendues (reste exact, arrondi au mètre, châssis), règlement d'un retour
(baisse de créance, remboursement borné, `CreditSaleReturned`) et cycle d'une demande de prix."""

from datetime import timedelta
from decimal import Decimal

import pytest

from app.domain.catalog.ids import ArticleId
from app.domain.sales.errors import RefundOverpayment, ReturnExceedsSold
from app.domain.sales.lines import SaleLine, SaleMode, SoldDetail
from app.domain.sales.price_request import PriceRequest, PriceRequestStatus
from app.domain.sales.receivable_events import CreditSaleReturned
from app.domain.sales.return_lines import AlreadyReturned, returned_line
from app.domain.sales.sale_return import Refund, SaleReturn
from app.domain.shared.errors import InvalidStateTransition, ValidationFailed
from app.domain.shared.ids import ShopId
from app.domain.shared.money import Money
from app.domain.shared.quantity import Quantity, StockUnit
from app.domain.shops.ids import LocationId, PaymentModeId
from app.domain.stock.values import StockCondition
from tests.contracts.catalog_data import NOW
from tests.contracts.sales_data import SELLER, customer, sale

SELLABLE = StockCondition.SELLABLE
NOW_SHOP = ShopId.new()


def meter_line() -> SaleLine:
    return SaleLine(
        article_id=ArticleId.new(),
        article_name="Bazin",
        sale_mode=SaleMode.METER,
        quantity=Decimal("2.5"),
        stock_quantity=Quantity.of("2.5", StockUnit.METER),
        unit_price=Money(1_001),
        frozen_last_cost=Money(501),
    )


def test_partial_returns_sum_to_the_line_exactly() -> None:
    line = meter_line()  # total 2 503 (2 502,5 arrondi), coût 1 253
    done = AlreadyReturned()
    first = returned_line(line, 1, "1.5", SELLABLE, done)
    assert (first.amount, first.cost) == (Money(1_502), Money(752))
    done.add(first)
    with pytest.raises(ReturnExceedsSold):
        returned_line(line, 1, "1.1", SELLABLE, done)
    last = returned_line(line, 1, "1", SELLABLE, done)
    assert (last.amount, last.cost, str(last.stock_quantity)) == (Money(1_001), Money(501), "1.0")
    assert first.amount + last.amount == line.line_total


def test_chassis_must_be_named_on_a_partial_line() -> None:
    line = SaleLine(
        article_id=ArticleId.new(),
        article_name="HJ",
        sale_mode=SaleMode.UNIT,
        quantity=Decimal(2),
        stock_quantity=Quantity.of(2, StockUnit.UNIT),
        unit_price=Money(780_000),
        details=(SoldDetail(chassis_number="A1"), SoldDetail(chassis_number="A2")),
    )
    with pytest.raises(ValidationFailed):
        returned_line(line, 1, 1, SELLABLE, AlreadyReturned())
    with pytest.raises(ValidationFailed):
        returned_line(line, 1, 1, SELLABLE, AlreadyReturned(), ("Z9",))
    full = returned_line(line, 1, 2, SELLABLE, AlreadyReturned())
    assert full.chassis == ("A1", "A2")
    assert full.margin is None


def test_credit_return_publishes_receivable_drop() -> None:
    buyer = customer(NOW_SHOP)
    sold = sale(NOW_SHOP, 1, customer_id=buyer.id)  # total 806 000, acompte 300 000
    lines = [returned_line(sold.content.lines[0], 1, 1, SELLABLE, AlreadyReturned())]
    refund = Refund(amount=Money(300_001), mode_id=PaymentModeId.new(), refunded_on=NOW.date())
    with pytest.raises(RefundOverpayment):  # 780 000 - 506 000 = 274 000 remboursables
        SaleReturn.record(
            sold, lines, reason="x", previous=[], refund=refund, performer=SELLER, now=NOW
        )
    made = SaleReturn.record(
        sold, lines, reason="x", previous=[], refund=None, performer=SELLER, now=NOW
    )
    assert made.credit_reduction == Money(506_000)
    drops = [e for e in made.events if isinstance(e, CreditSaleReturned)]
    assert [(d.sale_id, d.amount) for d in drops] == [(sold.id, Money(506_000))]
    assert made.margin == Money(240_000)


def test_price_request_lifecycle() -> None:
    request = PriceRequest.ask(
        NOW_SHOP,
        article=(ArticleId.new(), "HJ"),
        location_id=LocationId.new(),
        requested_price=Money(700_000),
        min_price=Money(720_000),
        performer=SELLER,
        now=NOW,
    )
    assert request.status_at(NOW + timedelta(minutes=29)) is PriceRequestStatus.PENDING
    assert request.status_at(NOW + timedelta(minutes=30)) is PriceRequestStatus.EXPIRED
    assert not request.expire(NOW + timedelta(minutes=10))
    with pytest.raises(InvalidStateTransition):
        request.use(sale(NOW_SHOP, 1).id, NOW)
    request.decide(accept=True, performer=SELLER, now=NOW + timedelta(minutes=20))
    assert request.usable_at(NOW + timedelta(minutes=49))
    assert request.expire(NOW + timedelta(minutes=50))
    assert not request.expire(NOW + timedelta(minutes=51))
    with pytest.raises(ValidationFailed):
        PriceRequest.ask(
            NOW_SHOP,
            article=(ArticleId.new(), "HJ"),
            location_id=LocationId.new(),
            requested_price=Money(720_000),
            min_price=Money(720_000),
            performer=SELLER,
            now=NOW,
        )
