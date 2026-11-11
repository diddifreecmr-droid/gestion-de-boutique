"""Répartition exacte au prorata (RG-T10, specs § 5.3 Costing) : exemples et propriétés."""

from decimal import Decimal
from fractions import Fraction

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.domain.shared.errors import InvalidAmount
from app.domain.shared.money import Money, Weight, allocate

weights_strategy = st.lists(st.integers(min_value=0, max_value=10**9), min_size=1, max_size=30)
totals = st.integers(min_value=0, max_value=10**12)


def test_even_split() -> None:
    assert allocate(Money(900), [1, 1, 1]) == [Money(300)] * 3


def test_remainder_goes_to_heaviest_weight() -> None:
    # 1000 sur 1/2/3 : 166,67 / 333,33 / 500 → 166 / 333 / 501 (reste 1 sur la plus forte).
    assert allocate(Money(1000), [1, 2, 3]) == [Money(166), Money(333), Money(501)]


def test_remainder_tie_goes_to_first_heaviest() -> None:
    assert allocate(Money(10), [1, 1, 1]) == [Money(4), Money(3), Money(3)]


def test_zero_weight_gets_nothing() -> None:
    assert allocate(Money(100), [0, 5, 0]) == [Money(0), Money(100), Money(0)]


def test_decimal_weights_for_meter_lines() -> None:
    # Lignes au mètre : quantité * prix au dixième, calcul exact sans flottant.
    weights: list[Weight] = [Decimal("2.5") * 1000, Decimal("0.5") * 1000]
    assert allocate(Money(600), weights) == [Money(500), Money(100)]


def test_zero_total() -> None:
    assert allocate(Money(0), [3, 4]) == [Money(0), Money(0)]


@pytest.mark.parametrize("weights", [[], [0, 0]])
def test_requires_a_positive_weight(weights: list[Weight]) -> None:
    with pytest.raises(InvalidAmount, match="aucun poids positif"):
        allocate(Money(10), weights)


@pytest.mark.parametrize("bad", [-1, Decimal("-0.1"), Decimal("NaN"), Decimal("Infinity")])
def test_rejects_negative_or_non_finite_weight(bad: Weight) -> None:
    with pytest.raises(InvalidAmount):
        allocate(Money(10), [1, bad])


@pytest.mark.parametrize("bad", [1.5, True, "1"])
def test_rejects_non_numeric_weight(bad: object) -> None:
    with pytest.raises(TypeError, match="poids"):
        allocate(Money(10), [1, bad])  # type: ignore[list-item]  # refus à l'exécution prouvé


def test_rejects_negative_total_and_non_money() -> None:
    with pytest.raises(InvalidAmount):
        allocate(Money(-1), [1])
    with pytest.raises(TypeError, match="Money"):
        allocate(10, [1])  # type: ignore[arg-type]  # refus à l'exécution prouvé ici


@given(totals, weights_strategy.filter(lambda ws: sum(ws) > 0))
def test_sum_is_exact_and_shares_are_non_negative(total: int, weights: list[int]) -> None:
    shares = allocate(Money(total), weights)
    assert len(shares) == len(weights)
    assert Money.total(shares) == Money(total)
    assert all(share.amount >= 0 for share in shares)
    assert all(share == Money(0) for share, w in zip(shares, weights, strict=True) if w == 0)


@given(totals, weights_strategy.filter(lambda ws: sum(ws) > 0))
def test_only_heaviest_share_carries_the_remainder(total: int, weights: list[int]) -> None:
    shares = allocate(Money(total), weights)
    weight_sum = sum(weights)
    heaviest = weights.index(max(weights))
    for index, (share, weight) in enumerate(zip(shares, weights, strict=True)):
        exact = Fraction(total * weight, weight_sum)
        gap = share.amount - exact
        if index == heaviest:
            assert -1 < gap < len(weights)
        else:
            assert -1 < gap <= 0
