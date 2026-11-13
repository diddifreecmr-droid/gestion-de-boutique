"""Domaine T29 : délai d'échange `exchange_days` inclusif (QC-4), échange hors délai sensible au
journal, réglage `employee_exchange_allowed` faux par défaut et booléen strict."""

from dataclasses import replace
from datetime import date

import pytest

from app.domain.sales import events as ev
from app.domain.sales.exchange_period import (
    ExchangePeriodOver,
    check_exchange_period,
    exchange_deadline,
)
from app.domain.sales.ids import SaleId
from app.domain.sales.return_lines import AlreadyReturned, returned_line
from app.domain.sales.sale_return import SaleReturn
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.ids import ShopId
from app.domain.shops.settings import SettingsValues
from app.domain.stock.values import StockCondition
from tests.contracts.catalog_data import NOW
from tests.contracts.sales_data import SELLER, sale

SOLD = date(2026, 11, 1)


def test_deadline_is_inclusive_and_optional() -> None:
    assert exchange_deadline(SOLD, 7) == date(2026, 11, 8)
    assert exchange_deadline(SOLD, 0) == SOLD  # le jour même
    assert exchange_deadline(SOLD, None) is None  # sans limite
    for bad in (-1, True):
        with pytest.raises(ValueError, match="exchange_days"):
            exchange_deadline(SOLD, bad)


@pytest.mark.parametrize(
    ("today", "days", "late"),
    [
        (date(2026, 11, 4), 7, False),  # J+3
        (date(2026, 11, 8), 7, False),  # J+7 : dernier jour
        (date(2026, 11, 9), 7, True),  # J+8
        (date(2026, 11, 2), 0, True),
        (date(2027, 11, 1), None, False),  # pas de délai
    ],
)
def test_owner_may_exceed(today: date, days: int | None, *, late: bool) -> None:
    assert check_exchange_period(SOLD, today, days, may_exceed=True) is late


def test_employee_is_refused_after_the_deadline() -> None:  # ERR3-02
    assert check_exchange_period(SOLD, date(2026, 11, 8), 7, may_exceed=False) is False
    with pytest.raises(ExchangePeriodOver) as raised:
        check_exchange_period(SOLD, date(2026, 11, 9), 7, may_exceed=False)
    assert raised.value.code == "EXCHANGE_PERIOD_OVER"
    assert raised.value.details == {
        "sold_on": "2026-11-01",
        "exchange_days": 7,
        "deadline": "2026-11-08",
    }


def _record(*, late: bool, exchange: bool = True) -> SaleReturn:
    sold = sale(ShopId.new(), 1)
    lines = [returned_line(sold.content.lines[0], 1, 1, StockCondition.SELLABLE, AlreadyReturned())]
    return SaleReturn.record(
        sold,
        lines,
        reason="autre taille",
        previous=[],
        refund=None,
        performer=SELLER,
        now=NOW,
        exchange_sale_id=SaleId.new() if exchange else None,
        late=late,
    )


def test_late_exchange_is_a_sensitive_journal_entry() -> None:  # AUD-L3-01
    [late] = [e for e in _record(late=True).events if isinstance(e, ev.SaleReturnRecorded)]
    assert isinstance(late, ev.SaleExchangedLate)
    assert late.audit_record().sensitive is True
    assert late.summary.startswith("Échange hors délai sur la vente")
    [normal] = [e for e in _record(late=False).events if isinstance(e, ev.SaleReturnRecorded)]
    assert type(normal) is ev.SaleReturnRecorded
    assert normal.audit_record().sensitive is False


def test_only_an_exchange_can_be_late() -> None:
    with pytest.raises(ValueError, match="échange"):
        _record(late=True, exchange=False)


def test_employee_exchange_setting_defaults_to_false() -> None:
    base = SettingsValues(
        receipt_format="58mm",  # type: ignore[arg-type]  # converti en ReceiptFormat
        paper_width_mm=58, printable_width_mm=48, margin_mm=2, font_size_pt=9, show_logo=False,
    )  # fmt: skip
    assert base.employee_exchange_allowed is False
    assert replace(base, employee_exchange_allowed=True).scalars()["employee_exchange_allowed"]
    with pytest.raises(ValidationFailed) as raised:
        replace(base, employee_exchange_allowed="oui")  # type: ignore[arg-type]  # type faux testé
    assert raised.value.details == {"field": "employee_exchange_allowed"}
