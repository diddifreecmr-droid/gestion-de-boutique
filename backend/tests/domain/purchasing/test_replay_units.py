"""Rejeu du CMP sur le stock réel (Q-02, SCN-04 v3 : 515 000), dernier coût (RG-T11, Q-04),
unités de saisie (RG-X02 : 10 yd → 9,1 m) et instant d'entrée d'un achat."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from app.domain.purchasing.replay import CostEvent, replay_wac
from app.domain.purchasing.units import EntryUnit, to_stock_quantity
from app.domain.purchasing.values import entry_instant
from app.domain.shared.errors import InvalidQuantity, ValidationFailed
from app.domain.shared.ids import uuid7
from app.domain.shared.money import Money
from app.domain.shared.quantity import StockUnit

DAY1 = datetime(2026, 11, 1, 8, tzinfo=UTC)


def event(day: int, quantity: int, cost: int | None = None, order: UUID | None = None) -> CostEvent:
    return CostEvent(
        at=DAY1 + timedelta(days=day),
        order=order or uuid7(),
        quantity=Decimal(quantity),
        unit_cost=None if cost is None else Money(cost),
        sets_cost=cost is not None,
    )


def test_replay_on_real_stock_gives_515000() -> None:
    p1, sale, p2 = event(0, 10, 500_000), event(0, -5), event(1, 5, 530_000)
    state = replay_wac([p2, sale, p1])  # ordre d'entrée indifférent : tri chronologique
    assert (state.quantity, state.wac, state.last_cost) == (
        Decimal(10),
        Money(515_000),
        Money(530_000),
    )
    without_sale = replay_wac([p1, p2])
    assert without_sale.wac == Money(510_000)  # SCN-02 / SCN-04 v1


def test_exits_and_neutral_entries_do_not_change_wac() -> None:
    state = replay_wac([event(0, 10, 500_000), event(1, -3), event(2, 2), event(3, -1)])
    assert (state.quantity, state.wac) == (Decimal(8), Money(500_000))
    assert replay_wac([]).wac is None


def test_last_cost_by_date_then_recording_order() -> None:
    first, second = uuid7(), uuid7()
    late_recorded_older = event(0, 1, 400_000, order=second)
    same_day = event(1, 1, 450_000, order=first)
    later_same_day = event(1, 1, 470_000, order=second)
    assert replay_wac([same_day, late_recorded_older]).last_cost == Money(450_000)
    assert replay_wac([later_same_day, same_day]).last_cost == Money(470_000)  # Q-04


def test_cost_event_guards() -> None:
    with pytest.raises(ValueError, match="coût"):
        CostEvent(at=DAY1, order=uuid7(), quantity=Decimal(1), sets_cost=True)
    with pytest.raises(TypeError):
        CostEvent(at=DAY1, order=uuid7(), quantity=1)  # type: ignore[arg-type]


def test_entry_units_rg_x02() -> None:
    meter = StockUnit.METER
    assert str(to_stock_quantity(Decimal(10), EntryUnit.YARD, meter)) == "9.1"
    assert str(to_stock_quantity(Decimal(3), EntryUnit.PIECE, meter, Decimal("5.5"))) == "16.5"
    assert str(to_stock_quantity(Decimal(2), EntryUnit.PIECE, meter, Decimal("2.75"))) == "5.5"
    assert str(to_stock_quantity(Decimal("2.5"), EntryUnit.METER, meter)) == "2.5"
    assert str(to_stock_quantity(Decimal(4), EntryUnit.UNIT, StockUnit.UNIT)) == "4"
    for unit, stock, length in (
        (EntryUnit.YARD, StockUnit.UNIT, None),
        (EntryUnit.METER, StockUnit.PIECE, None),
    ):
        with pytest.raises(ValidationFailed) as refused:
            to_stock_quantity(Decimal(1), unit, stock, length)
        assert refused.value.details["field"] == "unit"
    with pytest.raises(ValidationFailed) as no_length:  # SCN-L3-03 : pièce sans longueur
        to_stock_quantity(Decimal(3), EntryUnit.PIECE, meter, None)
    assert no_length.value.details["field"] == "piece_length_m"
    for bad in ("0", "-1", "1.5"):
        with pytest.raises(InvalidQuantity):
            to_stock_quantity(Decimal(bad), EntryUnit.UNIT, StockUnit.UNIT)  # PUR-04


def test_entry_instant_follows_purchase_date() -> None:
    received = datetime(2026, 11, 10, 8, tzinfo=UTC)  # 09 h à Douala
    assert entry_instant(date(2026, 11, 10), received) == received
    assert entry_instant(date(2026, 11, 3), received) == datetime(2026, 11, 2, 23, tzinfo=UTC)
