"""Présentation des Coûts et marges (specs § 15.1) : aucun calcul ici (`application/reporting/
margins.py`), seulement la mise en forme des quantités, longueurs et taux en chaînes."""

from decimal import Decimal

from app.application.reporting.margins import (
    ArticleMargin,
    DayMargin,
    FabricMargin,
    Figures,
    PerUnit,
)
from app.application.reporting.use_cases.margins import MarginsReport
from app.interface.http.presenters.reporting import period_out
from app.interface.http.schemas import reporting_margins as s


def _text(value: Decimal | None) -> str | None:
    return None if value is None else format(value.normalize(), "f")


def _figures(f: Figures) -> s.MarginFigures:
    rate = None if f.margin_rate is None else f"{f.margin_rate:.2f}"
    return s.MarginFigures(
        revenue=f.revenue, cost=f.cost, margin=f.margin, margin_rate=rate,
        without_cost=f.without_cost,
    )  # fmt: skip


def _unit(u: PerUnit | None) -> s.PerUnitOut | None:
    return None if u is None else s.PerUnitOut(price=u.price, cost=u.cost, margin=u.margin)


def _article(a: ArticleMargin) -> s.ArticleMarginOut:
    return s.ArticleMarginOut(
        article_id=a.article_id.value,
        name=a.name,
        fabric=a.fabric,
        stock_unit=a.stock_unit.value,
        quantity=format(a.quantity.normalize(), "f"),
        figures=_figures(a.figures),
        roll_length_m=_text(a.roll_length_m),
        per_meter=_unit(a.per_meter),
        per_roll=_unit(a.per_roll),
    )


def _fabric(f: FabricMargin) -> s.FabricMarginOut:
    return s.FabricMarginOut(
        fabric=f.fabric,
        colors=f.colors,
        quantity=format(f.quantity.normalize(), "f"),
        figures=_figures(f.figures),
        roll_length_m=_text(f.roll_length_m),
        per_meter=_unit(f.per_meter),
        per_roll=_unit(f.per_roll),
    )


def _day(d: DayMargin) -> s.DayMarginOut:
    return s.DayMarginOut(day=d.day, revenue=d.revenue, cost=d.cost, margin=d.margin)


def margins_response(report: MarginsReport) -> s.MarginsResponse:
    return s.MarginsResponse(
        period=period_out(report.period),
        totals=_figures(report.totals),
        articles=[_article(a) for a in report.articles],
        fabrics=[_fabric(f) for f in report.fabrics],
        days=[_day(d) for d in report.days],
    )
