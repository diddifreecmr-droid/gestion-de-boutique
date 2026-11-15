"""Indicateurs « Coûts et marges » (`application/reporting/margins.py`) : taux de marge, lignes
sans coût, Textile au mètre et au rouleau, regroupement par tissu, série jour par jour."""

from datetime import date
from decimal import Decimal

from app.application.reporting.margin_ports import ArticleDaySales
from app.application.reporting.margins import (
    PerUnit,
    article_margins,
    day_margins,
    fabric_margins,
    figures_of,
)
from app.domain.catalog.ids import ArticleId
from app.domain.shared.quantity import StockUnit

D1, D2 = date(2026, 11, 9), date(2026, 11, 10)
RED, GREEN, MOTO = ArticleId.new(), ArticleId.new(), ArticleId.new()


def _cloth(day: date, article: ArticleId, color: str, meters: int, price: int, cost: int,
           length: str = "25") -> ArticleDaySales:  # fmt: skip
    return ArticleDaySales(
        day=day, article_id=article, name=f"Djampar — {color}", fabric="Djampar",
        stock_unit=StockUnit.METER, roll_length_m=Decimal(length), quantity=Decimal(meters),
        costed_quantity=Decimal(meters), revenue=meters * price, costed_revenue=meters * price,
        cost=meters * cost,
    )  # fmt: skip


ROWS = [
    _cloth(D1, RED, "Rouge", 25, 4_000, 3_000),
    _cloth(D2, RED, "Rouge", 5, 4_000, 3_000),
    _cloth(D2, GREEN, "Vert", 10, 5_000, 3_000),
    ArticleDaySales(
        day=D2,
        article_id=MOTO,
        name="Haojue",
        fabric=None,
        stock_unit=StockUnit.UNIT,
        roll_length_m=None,
        quantity=Decimal(2),
        costed_quantity=Decimal(1),
        revenue=1_500_000,
        costed_revenue=800_000,
        cost=550_000,
        without_cost=1,
    ),
]


def test_totals_exclude_lines_without_cost_from_margin_and_rate() -> None:
    totals = figures_of(ROWS)
    assert (totals.revenue, totals.cost, totals.margin) == (1_670_000, 670_000, 300_000)
    assert totals.margin_rate == Decimal("30.93")
    assert totals.without_cost == 1
    assert figures_of([]).margin_rate is None


def test_textile_per_meter_and_per_roll_and_fabric_grouping() -> None:
    by_name = {a.name: a for a in article_margins(ROWS)}
    red = by_name["Djampar — Rouge"]
    assert (red.quantity, red.roll_length_m) == (Decimal(30), Decimal(25))
    assert red.per_meter == PerUnit(price=4_000, cost=3_000, margin=1_000)
    assert red.per_roll == PerUnit(price=100_000, cost=75_000, margin=25_000)
    assert (by_name["Haojue"].per_meter, by_name["Haojue"].per_roll) == (None, None)
    [fabric] = fabric_margins(ROWS)
    assert (fabric.fabric, fabric.colors, fabric.quantity) == ("Djampar", 2, Decimal(40))
    assert fabric.per_meter == PerUnit(price=4_250, cost=3_000, margin=1_250)
    assert fabric.per_roll == PerUnit(price=106_250, cost=75_000, margin=31_250)
    mixed = [*ROWS, _cloth(D2, ArticleId.new(), "Bleu", 1, 4_000, 3_000, length="30")]
    assert fabric_margins(mixed)[0].per_roll is None  # longueurs différentes


def test_days_cover_the_whole_period() -> None:
    days = day_margins([date(2026, 11, 8), D1, D2], ROWS)
    assert [(d.day, d.margin) for d in days] == [
        (date(2026, 11, 8), 0),
        (D1, 25_000),
        (D2, 275_000),
    ]
