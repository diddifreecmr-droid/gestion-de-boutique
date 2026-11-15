"""Indicateurs « Coûts et marges » (specs § 15.1, 2026-11-15) tirés des sommes de `MarginQueries`.

- marge = chiffre d'affaires des lignes à coût connu - coût figé ; taux = marge / ce chiffre
  d'affaires, en pour cent à deux chiffres après la virgule ; lignes sans coût comptées à part ;
- Textile (unité de stock : mètre) : prix, coût et marge **au mètre** (sommes / mètres à coût
  connu) et **au rouleau** (au mètre x longueur du rouleau de l'article) ;
- regroupement par tissu (`fabric`) : somme des couleurs ; rouleau seulement si toutes les
  couleurs ont la même longueur ;
- série par jour : chaque jour de la période, jours sans vente à zéro.
"""

from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.application.reporting.margin_ports import ArticleDaySales
from app.domain.catalog.ids import ArticleId
from app.domain.shared.quantity import StockUnit


@dataclass(frozen=True, slots=True, kw_only=True)
class Figures:
    revenue: int
    cost: int
    margin: int
    margin_rate: Decimal | None
    """Pour cent, deux chiffres après la virgule ; `None` sans chiffre d'affaires à coût connu."""
    without_cost: int


@dataclass(frozen=True, slots=True, kw_only=True)
class PerUnit:
    """Prix, coût et marge d'un mètre ou d'un rouleau (francs arrondis)."""

    price: int
    cost: int
    margin: int


@dataclass(frozen=True, slots=True, kw_only=True)
class ArticleMargin:
    article_id: ArticleId
    name: str
    fabric: str | None
    stock_unit: StockUnit
    quantity: Decimal
    figures: Figures
    roll_length_m: Decimal | None = None
    per_meter: PerUnit | None = None
    per_roll: PerUnit | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class FabricMargin:
    fabric: str
    colors: int
    quantity: Decimal
    figures: Figures
    roll_length_m: Decimal | None = None
    per_meter: PerUnit | None = None
    per_roll: PerUnit | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class DayMargin:
    day: date
    revenue: int
    cost: int
    margin: int


def _franc(value: Decimal) -> int:
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def figures_of(rows: Sequence[ArticleDaySales]) -> Figures:
    costed = sum(r.costed_revenue for r in rows)
    cost = sum(r.cost for r in rows)
    margin = costed - cost
    rate = None if costed == 0 else (Decimal(margin * 100) / costed).quantize(Decimal("0.01"))
    return Figures(
        revenue=sum(r.revenue for r in rows),
        cost=cost,
        margin=margin,
        margin_rate=rate,
        without_cost=sum(r.without_cost for r in rows),
    )


def _per_meter(rows: Sequence[ArticleDaySales]) -> PerUnit | None:
    meters = sum((r.costed_quantity for r in rows), Decimal(0))
    if meters == 0:
        return None
    price = Decimal(sum(r.costed_revenue for r in rows)) / meters
    cost = Decimal(sum(r.cost for r in rows)) / meters
    return PerUnit(price=_franc(price), cost=_franc(cost), margin=_franc(price - cost))


def _per_roll(rows: Sequence[ArticleDaySales], length: Decimal | None) -> PerUnit | None:
    meter = _per_meter(rows)
    if meter is None or length is None:
        return None
    price, cost = _franc(meter.price * length), _franc(meter.cost * length)
    return PerUnit(price=price, cost=cost, margin=price - cost)


def _textile(rows: Sequence[ArticleDaySales]) -> bool:
    return all(r.stock_unit is StockUnit.METER for r in rows)


def _length(rows: Sequence[ArticleDaySales]) -> Decimal | None:
    lengths = {r.roll_length_m for r in rows}
    return lengths.pop() if len(lengths) == 1 else None


def article_margins(rows: Iterable[ArticleDaySales]) -> list[ArticleMargin]:
    """Par article, de la plus forte marge à la plus faible (puis par nom)."""
    groups: dict[ArticleId, list[ArticleDaySales]] = defaultdict(list)
    for row in rows:
        groups[row.article_id].append(row)
    found = []
    for article_id, group in groups.items():
        last, textile, length = group[-1], _textile(group), _length(group)
        found.append(
            ArticleMargin(
                article_id=article_id,
                name=last.name,
                fabric=last.fabric,
                stock_unit=last.stock_unit,
                quantity=sum((r.quantity for r in group), Decimal(0)),
                figures=figures_of(group),
                roll_length_m=length if textile else None,
                per_meter=_per_meter(group) if textile else None,
                per_roll=_per_roll(group, length) if textile else None,
            )
        )
    return sorted(found, key=lambda a: (-a.figures.margin, a.name))


def fabric_margins(rows: Iterable[ArticleDaySales]) -> list[FabricMargin]:
    """Par tissu (articles qui ont un `fabric`), de la plus forte marge à la plus faible."""
    groups: dict[str, list[ArticleDaySales]] = defaultdict(list)
    for row in rows:
        if row.fabric is not None:
            groups[row.fabric].append(row)
    found = []
    for fabric, group in groups.items():
        textile, length = _textile(group), _length(group)
        found.append(
            FabricMargin(
                fabric=fabric,
                colors=len({r.article_id for r in group}),
                quantity=sum((r.quantity for r in group), Decimal(0)),
                figures=figures_of(group),
                roll_length_m=length if textile else None,
                per_meter=_per_meter(group) if textile else None,
                per_roll=_per_roll(group, length) if textile else None,
            )
        )
    return sorted(found, key=lambda f: (-f.figures.margin, f.fabric))


def day_margins(days: Iterable[date], rows: Iterable[ArticleDaySales]) -> list[DayMargin]:
    groups: dict[date, list[ArticleDaySales]] = defaultdict(list)
    for row in rows:
        groups[row.day].append(row)
    result = []
    for day in days:
        figures = figures_of(groups.get(day, []))
        result.append(
            DayMargin(day=day, revenue=figures.revenue, cost=figures.cost, margin=figures.margin)
        )
    return result
