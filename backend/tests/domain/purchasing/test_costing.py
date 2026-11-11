"""Costing : répartition des frais (RG-T10, SCN-03), coût unitaire, CMP (RG-T12, SCN-02) et
règle d'arrondi (Q-03 : franc le plus proche, demi vers le haut) — exemples et propriétés."""

from decimal import Decimal
from fractions import Fraction

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.domain.catalog.ids import ArticleId
from app.domain.purchasing.costing import (
    allocate_fees,
    final_unit_cost,
    line_total,
    next_wac,
    round_franc,
)
from app.domain.purchasing.lines import FeeKind, PurchaseFee, PurchaseLine, cost_lines
from app.domain.purchasing.units import EntryUnit
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.money import Money
from app.domain.shared.quantity import Quantity, StockUnit

M = Money


def costed(*lines: tuple[int, int], fees: tuple[PurchaseFee, ...] = ()) -> list[tuple[int, int]]:
    items = [
        PurchaseLine(article_id=ArticleId.new(), quantity=Decimal(q), unit=EntryUnit.UNIT,
                     unit_price=M(p))
        for q, p in lines
    ]  # fmt: skip
    quantities = [Quantity.of(q, StockUnit.UNIT) for q, _ in lines]
    return [(c.fee_share.amount, c.unit_cost.amount) for c in cost_lines(items, quantities, fees)]


def test_scn01_customs_spread_on_twenty_motos() -> None:
    fee = PurchaseFee(kind=FeeKind.CUSTOMS, amount=M(400_000))
    assert costed((20, 520_000), fees=(fee,)) == [(400_000, 540_000)]  # CDC § 17.5 étape 1


def test_scn03_prorata_and_remainder_to_heaviest_line() -> None:
    transport = PurchaseFee(kind=FeeKind.TRANSPORT, amount=M(100_000))
    assert costed((2, 600_000), (1, 300_000), fees=(transport,)) == [
        (80_000, 640_000),
        (20_000, 320_000),
    ]  # a
    other = PurchaseFee(kind=FeeKind.OTHER, amount=M(100_000), label="manutention")
    assert costed((1, 100_000), (1, 200_000), fees=(other,)) == [
        (33_333, 133_333),
        (66_667, 266_667),
    ]  # b : le reste d'arrondi va à la ligne de plus forte valeur
    customs = PurchaseFee(kind=FeeKind.CUSTOMS, amount=M(100_000))
    [(share, unit)] = costed((3, 100_000), fees=(customs,))  # c
    assert (share, unit) == (100_000, 133_333)  # 133 333,33 → 133 333
    assert abs(3 * unit - 400_000) <= Fraction(3, 2)  # écart ≤ q/2 ; le total reste 400 000
    with pytest.raises(ValidationFailed) as refused:
        PurchaseFee(kind=FeeKind.OTHER, amount=M(1))  # d
    assert refused.value.details["field"] == "fees.label"


def test_scn02_wac_and_rounding_rule() -> None:
    assert next_wac(Decimal(10), M(500_000), Decimal(5), M(530_000)) == M(510_000)
    assert next_wac(Decimal(10), M(500_000), Decimal(3), M(530_000)) == M(506_923)
    assert next_wac(Decimal(0), M(500_000), Decimal(3), M(530_000)) == M(530_000)
    assert next_wac(Decimal(-2), M(500_000), Decimal(3), M(530_000)) == M(530_000)  # RG-T18
    assert next_wac(Decimal(4), None, Decimal(3), M(7)) == M(7)  # stock sans coût connu
    assert round_franc(Fraction(5, 2)) == M(3)  # demi vers le haut
    assert round_franc(Fraction(249, 100)) == M(2)
    with pytest.raises(ValueError, match="négatif"):
        round_franc(Fraction(-1, 2))


def test_textile_cost_per_meter_and_line_total_rounding() -> None:
    assert line_total(Decimal("0.5"), M(1_001)) == M(501)  # 500,5 → 501
    assert final_unit_cost(M(10_000), M(0), Decimal("9.1")) == M(1_099)  # 1 098,9 F/m
    with pytest.raises(ValueError, match="strictement positif"):
        final_unit_cost(M(1), M(0), Decimal(0))


def test_fees_edge_cases() -> None:
    assert allocate_fees([M(5), M(0)], []) == [M(0), M(0)]
    with pytest.raises(ValidationFailed):
        allocate_fees([M(0), M(0)], [M(10)])  # frais sur des lignes à 0 FCFA
    with pytest.raises(ValueError, match="au moins une ligne"):
        allocate_fees([], [M(1)])


values = st.lists(st.integers(0, 10**9), min_size=1, max_size=8)


@given(values, st.lists(st.integers(0, 10**7), max_size=4))
def test_allocate_fees_is_exact_and_non_negative(lines: list[int], fees: list[int]) -> None:
    if sum(fees) and not sum(lines):
        return
    shares = allocate_fees([M(v) for v in lines], [M(f) for f in fees])
    assert sum(s.amount for s in shares) == sum(fees)
    assert all(s.amount >= 0 for s in shares)
    assert all(s.amount == 0 for s, v in zip(shares, lines, strict=True) if v == 0)


@given(st.lists(st.tuples(st.integers(1, 50), st.integers(0, 2_000_000)), min_size=1, max_size=10))
def test_wac_stays_between_costs_without_exits(purchases: list[tuple[int, int]]) -> None:
    held, wac = Decimal(0), None
    for quantity, cost in purchases:
        wac = next_wac(held, wac, Decimal(quantity), M(cost))
        held += quantity
    costs = [cost for _, cost in purchases]
    assert wac is not None
    assert min(costs) <= wac.amount <= max(costs)
    assert next_wac(Decimal(0), None, Decimal(purchases[0][0]), M(costs[0])) == M(costs[0])
