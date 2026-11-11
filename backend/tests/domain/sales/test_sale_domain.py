"""Domaine des ventes : arrondi au mètre (T04), marges figées (RG-T14, RG-T15), règles de
paiement (RG-T20, Q-12, H20), modification (UC-VEN-07), annulation, événements pour T17."""

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.domain.audit.values import Performer
from app.domain.catalog.ids import ArticleId
from app.domain.purchasing.errors import ReasonRequired
from app.domain.purchasing.values import Capture
from app.domain.sales.errors import (
    CustomerRequired,
    LineChangeRefused,
    PaymentIncomplete,
    SaleOverpayment,
)
from app.domain.sales.ids import CustomerId, SaleId, SalePaymentId
from app.domain.sales.lines import SaleLine, SaleMode, SoldDetail
from app.domain.sales.payments import SalePayment
from app.domain.sales.receivable_events import (
    CreditSaleAmountsChanged,
    CreditSaleCancelled,
    CreditSaleRecorded,
)
from app.domain.sales.sale import Sale
from app.domain.sales.values import CreditTerms, SaleContent, SaleKind, sale_instant
from app.domain.shared.doc_number import DocNumber, DocType
from app.domain.shared.errors import InvalidAmount, InvalidStateTransition, ValidationFailed
from app.domain.shared.ids import DeviceId, ShopId, UserId
from app.domain.shared.money import Money
from app.domain.shared.quantity import Quantity, StockUnit
from app.domain.shops.ids import LocationId, PaymentModeId

NOW = datetime(2026, 11, 10, 9, 30, tzinfo=UTC)
WHO = Performer(UserId.new(), "seller", DeviceId.new())
CASH_MODE = PaymentModeId.new()


def moto_line(
    price: int = 780_000, cost: int | None = 540_000, wac: int | None = 540_000
) -> SaleLine:
    return SaleLine(
        article_id=ArticleId.new(),
        article_name="Haojue HJ125-8",
        sale_mode=SaleMode.UNIT,
        quantity=Decimal(1),
        stock_quantity=Quantity.of(1, StockUnit.UNIT),
        unit_price=Money(price),
        base_price=Money(780_000),
        frozen_last_cost=None if cost is None else Money(cost),
        frozen_wac=None if wac is None else Money(wac),
        details=(SoldDetail(color="Rouge", chassis_number="lbx 123"),),
    )


def paid(*amounts: int) -> tuple[SalePayment, ...]:
    return tuple(
        SalePayment(id=SalePaymentId.new(), mode_id=CASH_MODE, amount=Money(a)) for a in amounts
    )


def sale(kind: SaleKind, line: SaleLine, payments: tuple[SalePayment, ...], customer: bool) -> Sale:
    return Sale(
        id=SaleId.new(),
        shop_id=ShopId.new(),
        number=DocNumber(DocType.SALE, 1),
        kind=kind,
        location_id=LocationId.new(),
        seller_id=WHO.user_id,
        content=SaleContent(
            sold_on=date(2026, 11, 10),
            lines=(line,),
            payments=payments,
            customer_id=CustomerId.new() if customer else None,
        ),
        capture=Capture(WHO.user_id, DeviceId.new(), NOW, NOW),
        credit=CreditTerms(terms="100 000 par mois") if kind is SaleKind.CREDIT else None,
    )


def test_scn01_credit_sale_margins_and_receivable_event() -> None:
    credit = sale(SaleKind.CREDIT, moto_line(), paid(300_000), customer=True)
    credit.record(performer=WHO, below_minimum=False)
    assert (credit.total, credit.paid, credit.remaining) == (
        Money(780_000),
        Money(300_000),
        Money(480_000),
    )
    line = credit.content.lines[0]
    assert (line.margin, line.margin_wac) == (Money(240_000), Money(240_000))
    assert line.details[0].chassis_key == "LBX123"
    opened = [e for e in credit.events if isinstance(e, CreditSaleRecorded)]
    assert [(e.initial_amount, e.terms) for e in opened] == [(Money(480_000), "100 000 par mois")]


def test_unknown_cost_and_meter_rounding() -> None:
    assert moto_line(cost=None, wac=None).margin is None  # RG-T15 : non calculable
    meter = SaleLine(
        article_id=ArticleId.new(),
        article_name="Wax",
        sale_mode=SaleMode.METER,
        quantity=Decimal("2.5"),
        stock_quantity=Quantity.of("2.5", StockUnit.METER),
        unit_price=Money(1_001),
        frozen_last_cost=Money(301),
    )
    assert meter.line_total == Money(2_503)  # 2 502,5 → demi vers le haut
    assert meter.margin == Money(2_503 - 753)  # 2,5 x 301 = 752,5 → 753
    assert moto_line(price=500_000).margin == Money(-40_000)  # une marge peut être négative


def test_payment_rules() -> None:
    with pytest.raises(PaymentIncomplete):  # Q-12 : comptant payé en entier
        sale(SaleKind.CASH, moto_line(), paid(500_000), False).record(
            performer=WHO, below_minimum=False
        )
    with pytest.raises(SaleOverpayment):  # ERR-OVR-02
        sale(SaleKind.CASH, moto_line(), paid(500_000, 300_000), False).record(
            performer=WHO, below_minimum=False
        )
    with pytest.raises(CustomerRequired):  # H20
        sale(SaleKind.CREDIT, moto_line(), (), False).record(performer=WHO, below_minimum=False)
    with pytest.raises(ValidationFailed):  # crédit entièrement payé : « Comptant »
        sale(SaleKind.CREDIT, moto_line(), paid(780_000), True).record(
            performer=WHO, below_minimum=False
        )
    with pytest.raises(InvalidAmount):
        paid(0)


def test_modify_keeps_frozen_costs_and_refuses_line_changes() -> None:
    credit = sale(SaleKind.CREDIT, moto_line(), paid(300_000), customer=True)
    credit.record(performer=WHO, below_minimum=False)
    credit.events.pull()
    line = credit.content.lines[0]
    cheaper = SaleContent(
        sold_on=credit.content.sold_on,
        lines=(line.repriced(Money(760_000)),),
        payments=credit.content.payments,
        customer_id=credit.content.customer_id,
    )
    with pytest.raises(ReasonRequired):
        credit.modify(cheaper, reason=" ", performer=WHO, now=NOW)
    assert credit.modify(cheaper, reason="mauvais prix", performer=WHO, now=NOW)
    assert credit.content.lines[0].margin == Money(220_000)  # MOD-01
    changed = [e for e in credit.events if isinstance(e, CreditSaleAmountsChanged)]
    assert [e.initial_amount for e in changed] == [Money(460_000)]
    assert not credit.modify(cheaper, reason="rien", performer=WHO, now=NOW)
    other = replace(line, quantity=Decimal(2))
    with pytest.raises(LineChangeRefused):
        credit.modify(
            SaleContent(sold_on=date(2026, 11, 10), lines=(other,), customer_id=CustomerId.new()),
            reason="x",
            performer=WHO,
            now=NOW,
        )


def test_cancel_once_and_backdated_instant() -> None:
    credit = sale(SaleKind.CREDIT, moto_line(), paid(300_000), customer=True)
    credit.record(performer=WHO, below_minimum=False)
    credit.cancel("client a renoncé", refund_payments=True, performer=WHO, now=NOW)
    assert [e.refund_payments for e in credit.events if isinstance(e, CreditSaleCancelled)] == [
        True
    ]
    with pytest.raises(InvalidStateTransition):
        credit.cancel("encore", refund_payments=False, performer=WHO, now=NOW)
    assert sale_instant(date(2026, 11, 3), NOW) == datetime(2026, 11, 2, 23, tzinfo=UTC)
    with pytest.raises(ValidationFailed):
        SoldDetail(chassis_number="---")
