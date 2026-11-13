"""Présentation du Tableau de bord, des détails et des accueils (UC-TDB-01 à 05).

Le présentateur ne calcule aucun indicateur (définis dans `application/reporting/indicators.py`)
et n'ajoute aucun champ selon le rôle : l'accueil d'un rôle n'a **que** son bloc (le vendeur
n'a ni marge ni coût, le comptable ni vente ni chiffre d'affaires — RG-D02, RG-D03), décidé
par le cas d'utilisation ; les blocs absents sont exclus de la réponse.
"""

from decimal import Decimal
from typing import Any

from app.application.reporting.periods import Period
from app.application.reporting.use_cases.dashboard import DashboardReport, ReceivablesBlock
from app.application.reporting.use_cases.home import Home
from app.application.reporting.use_cases.read_details import DetailReport
from app.application.reporting.views import Compared, NotAvailable
from app.interface.http.presenters.stock import valuation_response
from app.interface.http.schemas import reporting as s


def _pct(value: Decimal | None) -> str | None:
    return None if value is None else f"{value:.2f}"


def _decimal(value: Decimal | None) -> str | None:
    return None if value is None else format(value.normalize(), "f")


def _period(period: Period) -> s.PeriodOut:
    return s.PeriodOut(
        kind=period.kind.value,
        first_day=period.first_day,
        last_day=period.last_day,
        days=period.days,
    )


def _compared(value: Compared) -> s.Compared:
    return s.Compared(value=value.value, previous=value.previous, change_pct=_pct(value.change))


def _lot(value: NotAvailable) -> s.NotAvailable:
    return s.NotAvailable(available=False, lot=value.lot, message=value.message)


def _lot_or_none(value: NotAvailable | None) -> s.NotAvailable | None:
    """`None` : module éteint pour la boutique (specs § 15.1)."""
    return None if value is None else _lot(value)


def _receivables(block: ReceivablesBlock | None) -> s.ReceivablesBlock | None:
    if block is None:
        return None
    return s.ReceivablesBlock(
        total_due=block.total_due,
        debtor_count=block.debtor_count,
        received=_compared(block.received),
        reminders_due=block.reminders_due,
    )


def dashboard_response(report: DashboardReport) -> s.DashboardResponse:
    summary, series, stock = report.summary, report.series, report.stock
    return s.DashboardResponse(
        period=_period(report.period),
        previous_period=_period(report.previous),
        summary=s.Summary(
            sales=_compared(summary.sales),
            sales_count=_compared(summary.sales_count),
            collected=_compared(summary.collected),
            margin=_compared(summary.margin),
            margin_wac=_compared(summary.margin_wac),
            margin_gap=summary.margin_gap,
            margin_rate_pct=_pct(summary.margin_rate),
            without_cost=summary.without_cost,
            expenses=None if summary.expenses is None else _compared(summary.expenses),
            result=_compared(summary.result),
        ),
        series=None
        if series is None
        else s.Series(
            points=[
                s.SeriesPoint(day=p.day, sales=p.sales, margin=p.margin) for p in series.points
            ],
            total_sales=series.total_sales,
            total_margin=series.total_margin,
            average_sales=series.average_sales,
            average_margin=series.average_margin,
        ),
        receivables=_receivables(report.receivables),
        stock=s.StockBlock(
            value=valuation_response(stock.sellable),
            damaged=valuation_response(stock.damaged),
            low_stock=stock.low_stock,
            to_verify=stock.to_verify,
            in_transit=_lot_or_none(report.transfers_in_transit),
        ),
        trucks=None
        if report.trucks is None or report.transport_expenses is None
        else s.TrucksBlock(
            trucks=_lot(report.trucks), transport_expenses=_lot(report.transport_expenses)
        ),
        alerts=s.AlertsBlock(
            error_reports=report.alerts.error_reports,
            price_requests=report.alerts.price_requests,
        ),
    )


def detail_response(report: DetailReport) -> s.DashboardDetailResponse:
    return s.DashboardDetailResponse(
        metric=report.metric.value,
        period=_period(report.period),
        total=report.total,
        lines=[
            s.DetailLineOut(
                kind=line.kind.value,
                id=str(line.id),
                label=line.label,
                day=line.day,
                amount=line.amount,
                count=line.count,
                margin=line.margin,
                quantity=_decimal(line.quantity),
                threshold=_decimal(line.threshold),
            )
            for line in report.lines
        ],
    )


def home_response(home: Home) -> s.HomeResponse:
    fields: dict[str, Any] = {}
    if home.owner is not None:
        fields["owner"] = dashboard_response(home.owner)
    if home.seller is not None:
        seller = home.seller
        fields["seller"] = s.SellerHomeOut(
            sales_count=seller.sales_count,
            sales_amount=seller.sales_amount,
            reminders_due=seller.reminders_due,
            pending_uploads=seller.pending_uploads,
        )
    if home.accountant is not None:
        accountant = home.accountant
        fields["accountant"] = s.AccountantHomeOut(
            transfers_to_receive=_lot_or_none(accountant.transfers_to_receive),
            low_stock=accountant.low_stock,
            stock_value=valuation_response(accountant.stock_value),
            expenses=accountant.expenses,
        )
    if home.driver is not None:
        fields["driver"] = s.DriverHomeOut(
            current_trip=_lot_or_none(home.driver.current_trip),
            trip_expenses=_lot_or_none(home.driver.trip_expenses),
        )
    return s.HomeResponse(role=home.role.value, today=home.today, **fields)
