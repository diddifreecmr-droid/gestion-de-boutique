"""Quantity : Decimal au dixième, entière pour UNIT/PIECE, conversion yard (RG-T08, RG-X02)."""

from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.domain.shared.errors import InvalidQuantity
from app.domain.shared.quantity import Quantity, StockUnit, yards_to_meters

M = StockUnit.METER
U = StockUnit.UNIT
P = StockUnit.PIECE


@pytest.mark.parametrize("raw", ["2.5", Decimal("2.5"), "2.50", " 2.5 "])
def test_meter_accepts_one_decimal_and_normalizes(raw: str | Decimal) -> None:
    quantity = Quantity.of(raw, M)
    assert quantity.value == Decimal("2.5")
    assert str(quantity) == "2.5"


def test_meter_integer_is_written_with_one_decimal() -> None:
    assert str(Quantity.of(3, M)) == "3.0"


@pytest.mark.parametrize("raw", ["2.55", "0.01", Decimal("1.25")])
def test_more_than_one_decimal_is_refused(raw: str | Decimal) -> None:
    with pytest.raises(InvalidQuantity, match="une décimale") as excinfo:
        Quantity.of(raw, M)
    assert excinfo.value.code == "INVALID_QUANTITY"


@pytest.mark.parametrize("unit", [U, P])
def test_integral_units_refuse_decimals(unit: StockUnit) -> None:
    assert str(Quantity.of("3.0", unit)) == "3"
    with pytest.raises(InvalidQuantity, match="entière"):
        Quantity.of("2.5", unit)


def test_is_integral_flag() -> None:
    assert U.is_integral
    assert P.is_integral
    assert not M.is_integral


@pytest.mark.parametrize("bad", [2.5, True])
def test_float_and_bool_are_programming_errors(bad: object) -> None:
    with pytest.raises(TypeError, match="refusé"):
        Quantity.of(bad, M)  # type: ignore[arg-type]  # refus à l'exécution prouvé ici


def test_unsupported_types_are_refused() -> None:
    with pytest.raises(TypeError, match="non pris en charge"):
        Quantity.of(None, M)  # type: ignore[arg-type]  # refus à l'exécution prouvé ici
    with pytest.raises(TypeError, match="Decimal"):
        Quantity(2, M)  # type: ignore[arg-type]  # refus à l'exécution prouvé ici
    with pytest.raises(TypeError, match="Unité"):
        Quantity(Decimal(2), "METER")  # type: ignore[arg-type]  # refus à l'exécution prouvé


@pytest.mark.parametrize("raw", ["abc", "", "NaN", "Infinity", "1e11", "-1e11"])
def test_unreadable_or_out_of_bounds(raw: str) -> None:
    with pytest.raises(InvalidQuantity):
        Quantity.of(raw, M)


def test_negative_zero_is_canonical() -> None:
    assert str(Quantity.of("-0.0", M)) == "0.0"


def test_signed_quantity_and_entry_rules() -> None:
    delta = Quantity.of(-2, U)
    assert delta.value == Decimal(-2)
    assert Quantity.of(1, U).require_positive("q") == Quantity.of(1, U)
    assert Quantity.zero(U).require_non_negative("q") == Quantity.zero(U)
    with pytest.raises(InvalidQuantity, match="strictement positive"):
        Quantity.zero(U).require_positive("q")
    with pytest.raises(InvalidQuantity, match="négative") as excinfo:
        delta.require_non_negative("qty")
    assert excinfo.value.details["field"] == "qty"


def test_arithmetic_and_ordering_same_unit() -> None:
    assert Quantity.of("2.5", M) + Quantity.of("0.5", M) == Quantity.of(3, M)
    assert Quantity.of("2.5", M) - Quantity.of("3", M) == Quantity.of("-0.5", M)
    assert -Quantity.of(2, U) == Quantity.of(-2, U)
    assert Quantity.of(1, U) < Quantity.of(2, U) <= Quantity.of(2, U)
    assert len({Quantity.of("2.5", M), Quantity.of("2.50", M)}) == 1


def test_units_never_mix() -> None:
    assert Quantity.of(1, U) != Quantity.of(1, P)
    with pytest.raises(ValueError, match="incompatibles"):
        Quantity.of(1, U) + Quantity.of(1, P)
    with pytest.raises(ValueError, match="incompatibles"):
        Quantity.of(1, U) - Quantity.of(1, P)
    with pytest.raises(ValueError, match="incompatibles"):
        _ = Quantity.of(1, U) < Quantity.of(1, P)


def test_no_mixing_with_plain_numbers() -> None:
    assert Quantity.of(1, U) != 1
    with pytest.raises(TypeError):
        Quantity.of(1, U) + 1  # type: ignore[operator]  # refus à l'exécution prouvé ici
    with pytest.raises(TypeError):
        Quantity.of(1, U) - 1  # type: ignore[operator]  # refus à l'exécution prouvé ici
    with pytest.raises(TypeError):
        _ = Quantity.of(1, U) < 1  # type: ignore[operator]  # refus à l'exécution prouvé ici


@pytest.mark.parametrize(
    ("yards", "meters"),
    [(10, "9.1"), ("0.5", "0.5"), ("1", "0.9"), ("100", "91.4"), (0, "0.0"), ("12.5", "11.4")],
)
def test_yards_to_meters_rounds_half_up_to_tenth(yards: str | int, meters: str) -> None:
    assert yards_to_meters(yards) == Quantity.of(meters, M)


def test_yards_input_follows_quantity_rules() -> None:
    with pytest.raises(InvalidQuantity, match="une décimale"):
        yards_to_meters("1.25")
    with pytest.raises(InvalidQuantity, match="négative"):
        yards_to_meters(-1)


@given(st.integers(min_value=0, max_value=10**8))
def test_yard_conversion_error_is_at_most_half_a_tenth(tenths_of_yard: int) -> None:
    yards = Decimal(tenths_of_yard) / 10
    meters = yards_to_meters(yards)
    assert abs(meters.value - yards * Decimal("0.9144")) <= Decimal("0.05")
