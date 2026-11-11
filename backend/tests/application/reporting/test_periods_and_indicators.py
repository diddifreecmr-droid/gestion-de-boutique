"""Périodes (UC-TDB-02) et définition des indicateurs (§ 14.1) : fonctions pures."""

from datetime import date
from decimal import Decimal

import pytest

from app.application.reporting.indicators import (
    Figures,
    Inputs,
    average,
    change,
    daily_figures,
    total_of,
)
from app.application.reporting.periods import (
    MAX_PERIOD_DAYS,
    Period,
    PeriodKind,
    resolve_period,
)
from app.application.reporting.ports import (
    ExpenseFlow,
    FlowKind,
    MoneyFlow,
    ReturnsDay,
    SalesDay,
)
from app.application.reporting.views import series_of, summary_of
from app.domain.shared.errors import ValidationFailed
from app.domain.shops.ids import ExpenseCategoryId, PaymentModeId

TUESDAY = date(2026, 11, 10)


@pytest.mark.parametrize(
    ("kind", "first", "last"),
    [
        (PeriodKind.TODAY, date(2026, 11, 10), date(2026, 11, 10)),
        (PeriodKind.YESTERDAY, date(2026, 11, 9), date(2026, 11, 9)),
        (PeriodKind.WEEK, date(2026, 11, 9), date(2026, 11, 10)),
        (PeriodKind.MONTH, date(2026, 11, 1), date(2026, 11, 10)),
        (PeriodKind.LAST_MONTH, date(2026, 10, 1), date(2026, 10, 31)),
    ],
)
def test_named_periods(kind: PeriodKind, first: date, last: date) -> None:
    period = resolve_period(kind, TUESDAY)
    assert (period.first_day, period.last_day) == (first, last)


def test_week_on_monday_and_sunday_and_january_last_month() -> None:
    monday = resolve_period(PeriodKind.WEEK, date(2026, 11, 9))
    assert (monday.first_day, monday.days) == (date(2026, 11, 9), 1)
    sunday = resolve_period(PeriodKind.WEEK, date(2026, 11, 15))
    assert (sunday.first_day, sunday.days) == (date(2026, 11, 9), 7)
    january = resolve_period(PeriodKind.LAST_MONTH, date(2027, 1, 15))
    assert (january.first_day, january.last_day) == (date(2026, 12, 1), date(2026, 12, 31))
    assert january.previous() == Period(
        PeriodKind.LAST_MONTH, date(2026, 10, 31), date(2026, 11, 30)
    )


def test_custom_period_rules() -> None:
    custom = resolve_period(PeriodKind.CUSTOM, TUESDAY, date(2026, 11, 1), TUESDAY)
    assert custom.days == 10
    errors = [
        (None, TUESDAY),
        (TUESDAY, None),
        (TUESDAY, date(2026, 11, 11)),
        (date(2025, 1, 1), TUESDAY),
        (TUESDAY, date(2026, 11, 9)),
    ]
    for first, last in errors:
        with pytest.raises(ValidationFailed):
            resolve_period(PeriodKind.CUSTOM, TUESDAY, first, last)
    with pytest.raises(ValidationFailed):
        resolve_period(PeriodKind.TODAY, TUESDAY, None, TUESDAY)
    assert MAX_PERIOD_DAYS == 366


def test_change_rate_and_average() -> None:
    assert change(2_310_000, 800_000) == Decimal("188.75")
    assert change(800_000, 2_310_000) == Decimal("-65.37")
    assert change(-50_000, 50_000) == Decimal("-200.00")
    assert change(10, 0) is None
    assert Figures(sales=2_310_000, margin=660_000).margin_rate == Decimal("28.57")
    assert Figures(sales=0, margin=10).margin_rate is None
    assert average(800_000, 30) == 26_667
    with pytest.raises(ValueError, match="jours"):
        average(1, 0)


def test_daily_figures_combine_every_source() -> None:
    mode, category = PaymentModeId.new(), ExpenseCategoryId.new()
    inputs = Inputs(
        sold=[
            SalesDay(
                day=TUESDAY,
                count=2,
                total=1_500_000,
                margin=400_000,
                margin_wac=440_000,
                without_cost=1,
                without_wac=1,
            )
        ],
        cancelled=[
            SalesDay(day=TUESDAY, count=1, total=700_000, margin=150_000, margin_wac=170_000)
        ],
        returns=[
            ReturnsDay(day=TUESDAY, count=1, amount=100_000, margin=30_000, margin_wac=35_000)
        ],
        flows=[
            MoneyFlow(
                day=TUESDAY, kind=FlowKind.SALE_CASH, mode_id=mode, amount=1_500_000, count=2
            ),
            MoneyFlow(
                day=TUESDAY, kind=FlowKind.SALE_CANCELLED, mode_id=mode, amount=700_000, count=1
            ),
            MoneyFlow(day=TUESDAY, kind=FlowKind.INSTALLMENT, mode_id=mode, amount=50_000, count=1),
            MoneyFlow(day=TUESDAY, kind=FlowKind.REFUND, mode_id=mode, amount=100_000, count=1),
        ],
        expenses=[
            ExpenseFlow(day=TUESDAY, category_id=category, amount=35_000, count=2, cancelled=False),
            ExpenseFlow(day=TUESDAY, category_id=category, amount=10_000, count=1, cancelled=True),
        ],
    )
    [day] = daily_figures([TUESDAY], inputs)
    assert day.figures == Figures(
        sales=700_000,
        sales_count=1,
        collected=750_000,
        margin=220_000,
        margin_wac=235_000,
        without_cost=1,
        expenses=25_000,
        installments=50_000,
    )
    assert (day.figures.result, day.figures.margin_gap) == (195_000, 15_000)
    empty = daily_figures([date(2026, 11, 11)], inputs)
    assert empty[0].figures == Figures()


def test_summary_and_series() -> None:
    days = daily_figures(
        [date(2026, 11, 9), TUESDAY],
        Inputs(
            sold=[SalesDay(day=TUESDAY, count=1, total=780_000, margin=230_000)],
            cancelled=[],
            returns=[],
            flows=[],
            expenses=[],
        ),
    )
    series = series_of(days)
    assert series is not None
    assert (series.total_sales, series.average_sales, series.average_margin) == (
        780_000,
        390_000,
        115_000,
    )
    assert series_of(days[:1]) is None
    summary = summary_of(total_of(days), Figures(sales=390_000))
    assert (summary.sales.value, summary.sales.change) == (780_000, Decimal("100.00"))
    assert summary.result.value == 230_000
