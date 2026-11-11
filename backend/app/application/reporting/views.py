"""Vues du tableau de bord (UC-TDB-01 à 03) construites à partir de `indicators.py`.

- `Compared` : valeur, valeur de la période précédente et variation en % (`None` si la
  précédente vaut 0) — la « flèche et le pourcentage » de UC-TDB-01.
- `Series` : pour une période de plusieurs jours, ventes et marge jour par jour, total et
  moyenne par jour (UC-TDB-02) ; absente pour une seule journée.
- `NotAvailable` : indicateur prévu au CDC mais livré au Lot 2 (déplacements, camions,
  dépenses de transport) — renvoyé **explicitement**, jamais comme un 0 trompeur.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.application.reporting.indicators import DayFigures, Figures, average, change, total_of


@dataclass(frozen=True, slots=True)
class NotAvailable:
    lot: int = 2
    message: str = "Non disponible au Lot 1"


LOT_2 = NotAvailable()


@dataclass(frozen=True, slots=True)
class Compared:
    value: int
    previous: int

    @property
    def change(self) -> Decimal | None:
        return change(self.value, self.previous)


@dataclass(frozen=True, slots=True, kw_only=True)
class Summary:
    """Flux de la période, comparés à la période précédente de même longueur."""

    sales: Compared
    sales_count: Compared
    collected: Compared
    margin: Compared
    margin_wac: Compared
    margin_gap: int
    margin_rate: Decimal | None
    without_cost: int
    expenses: Compared
    result: Compared
    installments: Compared


def summary_of(current: Figures, previous: Figures) -> Summary:
    def pair(name: str) -> Compared:
        return Compared(getattr(current, name), getattr(previous, name))

    return Summary(
        sales=pair("sales"),
        sales_count=pair("sales_count"),
        collected=pair("collected"),
        margin=pair("margin"),
        margin_wac=pair("margin_wac"),
        margin_gap=current.margin_gap,
        margin_rate=current.margin_rate,
        without_cost=current.without_cost,
        expenses=pair("expenses"),
        result=pair("result"),
        installments=pair("installments"),
    )


@dataclass(frozen=True, slots=True)
class SeriesPoint:
    day: date
    sales: int
    margin: int


@dataclass(frozen=True, slots=True, kw_only=True)
class Series:
    points: list[SeriesPoint]
    total_sales: int
    total_margin: int
    average_sales: int
    average_margin: int


def series_of(days: list[DayFigures]) -> Series | None:
    """Série jour par jour ; `None` pour une seule journée (pas de graphique)."""
    if len(days) < 2:
        return None
    total = total_of(days)
    return Series(
        points=[SeriesPoint(d.day, d.figures.sales, d.figures.margin) for d in days],
        total_sales=total.sales,
        total_margin=total.margin,
        average_sales=average(total.sales, len(days)),
        average_margin=average(total.margin, len(days)),
    )
