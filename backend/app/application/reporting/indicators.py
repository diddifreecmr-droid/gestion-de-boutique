"""Définition des indicateurs du tableau de bord (CDC § 14.1) — **seul endroit** qui les calcule.

Pour une journée D (journée de Douala), à partir des sommes brutes du port `DashboardQueries` :

- **Ventes du jour** : totaux des ventes datées D (comptant et crédit pour leur total, H7),
  moins les totaux des ventes **annulées le jour D** quelle que soit leur date (Q-09), moins
  les montants des retours du jour D (Q-05).
- **Nombre de ventes** : ventes datées D - ventes annulées le jour D (un retour ne retire pas
  de vente).
- **Argent encaissé** (RG-T21) : paiements comptant + acomptes des ventes datées D +
  versements datés D - payé des ventes annulées le jour D - versements annulés le jour D -
  remboursements datés D.
- **Marge du jour** (RG-T14) : marges **connues** au dernier coût figé des lignes datées D -
  celles des ventes annulées le jour D - marges des retours du jour D.
- **Marge au CMP** (UC-TDB-03) : même calcul au CMP figé ; écart = CMP - dernier coût.
- **Ventes sans coût connu** (RG-T15) : lignes datées D à marge nulle - celles des ventes
  annulées le jour D ; leur marge n'est jamais comptée (ni 0, ni le prix de vente).
- **Taux de marge** : marge / ventes x 100, 2 décimales ; `None` si les ventes sont <= 0.
- **Dépenses du jour** : dépenses datées D - dépenses **annulées le jour D** (Q-09 appliquée
  aux dépenses : une journée passée ne bouge jamais).
- **Résultat simple** : marge du jour - dépenses du jour.
- **Versements reçus** : versements datés D - versements annulés le jour D (acomptes exclus,
  Q-24).

Une période de plusieurs jours est la somme de ses journées. Comparaison (« flèche et
pourcentage ») : `(valeur - précédente) / |précédente| x 100`, 2 décimales, `None` si la
précédente vaut 0. Arrondi demi vers le haut partout (comme les montants, T04).
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, fields
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.application.reporting.ports import (
    ExpenseFlow,
    FlowKind,
    MoneyFlow,
    ReturnsDay,
    SalesDay,
)

_CENT = Decimal("0.01")
_INSTALLMENTS = frozenset({FlowKind.INSTALLMENT, FlowKind.INSTALLMENT_CANCELLED})


@dataclass(frozen=True, slots=True, kw_only=True)
class Figures:
    """Indicateurs de flux d'une journée ou d'une période (tous en FCFA, sauf les nombres)."""

    sales: int = 0
    sales_count: int = 0
    collected: int = 0
    margin: int = 0
    margin_wac: int = 0
    without_cost: int = 0
    expenses: int = 0
    installments: int = 0

    @property
    def result(self) -> int:
        return self.margin - self.expenses

    @property
    def margin_gap(self) -> int:
        """Écart « marge au CMP - marge au dernier coût » (UC-TDB-03)."""
        return self.margin_wac - self.margin

    @property
    def margin_rate(self) -> Decimal | None:
        return None if self.sales <= 0 else percent(self.margin, self.sales)

    def __add__(self, other: "Figures") -> "Figures":
        values = {f.name: getattr(self, f.name) + getattr(other, f.name) for f in fields(self)}
        return Figures(**values)


@dataclass(frozen=True, slots=True, kw_only=True)
class DayFigures:
    day: date
    figures: Figures


@dataclass(frozen=True, slots=True, kw_only=True)
class Inputs:
    """Sommes brutes du port pour une période (voir `ports.py`)."""

    sold: list[SalesDay]
    cancelled: list[SalesDay]
    returns: list[ReturnsDay]
    flows: list[MoneyFlow]
    expenses: list[ExpenseFlow]


def percent(part: int, whole: int) -> Decimal:
    return (Decimal(part) * 100 / Decimal(whole)).quantize(_CENT, rounding=ROUND_HALF_UP)


def change(value: int, previous: int) -> Decimal | None:
    """Variation en % par rapport à la valeur précédente ; `None` si elle vaut 0."""
    return None if previous == 0 else percent(value - previous, abs(previous))


def average(total: int, days: int) -> int:
    """Moyenne par jour au franc près (demi vers le haut)."""
    if days <= 0:
        msg = f"Nombre de jours invalide : {days}"
        raise ValueError(msg)
    return int((Decimal(total) / days).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _sales(day: SalesDay, sign: int) -> Figures:
    return Figures(
        sales=sign * day.total,
        sales_count=sign * day.count,
        margin=sign * day.margin,
        margin_wac=sign * day.margin_wac,
        without_cost=sign * day.without_cost,
    )


def _return(day: ReturnsDay) -> Figures:
    return Figures(sales=-day.amount, margin=-day.margin, margin_wac=-day.margin_wac)


def _flow(flow: MoneyFlow) -> Figures:
    installments = flow.signed if flow.kind in _INSTALLMENTS else 0
    return Figures(collected=flow.signed, installments=installments)


def daily_figures(days: Iterable[date], inputs: Inputs) -> list[DayFigures]:
    """Indicateurs de chaque journée demandée (journées sans mouvement : zéros)."""
    by_day: dict[date, Figures] = defaultdict(Figures)
    for sold in inputs.sold:
        by_day[sold.day] += _sales(sold, 1)
    for cancelled in inputs.cancelled:
        by_day[cancelled.day] += _sales(cancelled, -1)
    for returned in inputs.returns:
        by_day[returned.day] += _return(returned)
    for flow in inputs.flows:
        by_day[flow.day] += _flow(flow)
    for expense in inputs.expenses:
        by_day[expense.day] += Figures(expenses=expense.signed)
    return [DayFigures(day=day, figures=by_day[day]) for day in days]


def total_of(days: Iterable[DayFigures]) -> Figures:
    return sum((d.figures for d in days), Figures())


def expenses_only(days: Iterable[date], flows: list[ExpenseFlow]) -> Figures:
    """Indicateurs des seules dépenses (accueil du comptable : aucune vente lue, RG-D03)."""
    empty = Inputs(sold=[], cancelled=[], returns=[], flows=[], expenses=flows)
    return total_of(daily_figures(days, empty))
