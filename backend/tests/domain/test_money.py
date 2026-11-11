"""Money : FCFA entiers signés, saisie jamais négative (H2, RG-T07)."""

from decimal import Decimal

import pytest

from app.domain.shared.errors import InvalidAmount
from app.domain.shared.money import BIGINT_MAX, BIGINT_MIN, Money


@pytest.mark.parametrize("bad", [1.0, Decimal(1), True, "100", None])
def test_non_int_amount_is_a_programming_error(bad: object) -> None:
    with pytest.raises(TypeError, match="int"):
        Money(bad)  # type: ignore[arg-type]  # on prouve justement le refus à l'exécution


def test_bigint_bounds_are_enforced() -> None:
    assert Money(BIGINT_MAX).amount == BIGINT_MAX
    assert Money(BIGINT_MIN).amount == BIGINT_MIN
    with pytest.raises(InvalidAmount) as excinfo:
        Money(BIGINT_MAX + 1)
    assert excinfo.value.code == "INVALID_AMOUNT"
    with pytest.raises(InvalidAmount):
        Money(BIGINT_MAX) + Money(1)


def test_computed_amount_may_be_negative() -> None:
    margin = Money(1000) - Money(1500)
    assert margin == Money(-500)
    assert margin.is_negative
    assert not Money(0).is_negative


def test_entry_amount_is_never_negative() -> None:
    assert Money.entry(0, "price") == Money(0)
    assert Money.entry(1500, "price") == Money(1500)
    with pytest.raises(InvalidAmount) as excinfo:
        Money.entry(-1, "price")
    assert dict(excinfo.value.details) == {"field": "price", "amount": -1}


def test_require_non_negative_returns_self() -> None:
    amount = Money(10)
    assert amount.require_non_negative("x") is amount
    with pytest.raises(InvalidAmount):
        (-amount).require_non_negative("x")


def test_arithmetic() -> None:
    assert Money(1000) + Money(250) == Money(1250)
    assert Money(1000) - Money(250) == Money(750)
    assert -Money(5) == Money(-5)
    assert Money(300) * 3 == Money(900)
    assert 3 * Money(300) == Money(900)
    assert Money(300) * -1 == Money(-300)


@pytest.mark.parametrize("factor", [1.5, Decimal(2), True])
def test_multiplication_only_by_int(factor: object) -> None:
    with pytest.raises(TypeError):
        Money(100) * factor  # type: ignore[operator]  # refus à l'exécution prouvé ici


def test_cannot_mix_with_plain_int() -> None:
    with pytest.raises(TypeError):
        Money(1) + 1  # type: ignore[operator]  # refus à l'exécution prouvé ici
    with pytest.raises(TypeError):
        Money(1) - 1  # type: ignore[operator]  # refus à l'exécution prouvé ici


def test_comparison_and_hash() -> None:
    assert Money(1) < Money(2) <= Money(2)
    assert Money(3) > Money(-3)
    assert Money(7) == Money(7)
    assert len({Money(7), Money(7), Money(8)}) == 2
    assert max([Money(1), Money(9), Money(4)]) == Money(9)


def test_total_of_iterable() -> None:
    assert Money.total([]) == Money.zero()
    assert Money.total(Money(n) for n in (100, -30, 5)) == Money(75)
    with pytest.raises(TypeError, match="Money"):
        Money.total([Money(1), 2])  # type: ignore[list-item]  # refus à l'exécution prouvé


def test_is_immutable() -> None:
    amount = Money(1)
    with pytest.raises(AttributeError):
        amount.amount = 2  # type: ignore[misc]  # on prouve justement l'immuabilité


@pytest.mark.parametrize(
    ("amount", "text"),
    [(0, "0 FCFA"), (950, "950 FCFA"), (1_250_000, "1 250 000 FCFA"), (-12_500, "-12 500 FCFA")],
)
def test_display_uses_space_between_thousands(amount: int, text: str) -> None:
    assert str(Money(amount)) == text
