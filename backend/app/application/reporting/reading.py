"""Lecture des sommes brutes d'une période par le port `DashboardQueries` (TR-21).

Une requête par famille de sommes, chacune bornée par la période (index de période, § 10) ;
les indicateurs sont ensuite calculés par `indicators.daily_figures`, jamais ici.
"""

from app.application.ports.uow import UnitOfWork
from app.application.reporting.indicators import DayFigures, Inputs, daily_figures
from app.application.reporting.periods import Period
from app.application.reporting.ports import DashboardQueries
from app.domain.shared.ids import UserId


def inputs_of(uow: UnitOfWork, period: Period, *, seller: UserId | None = None) -> Inputs:
    """Sommes de la période ; `seller` : ventes de ce vendeur seulement (ni argent ni dépenses,
    qui ne sont pas dans sa portée)."""
    queries = DashboardQueries.within(uow)
    first, last = period.first_day, period.last_day
    scoped = seller is not None
    return Inputs(
        sold=queries.sales_by_day(first, last, seller=seller),
        cancelled=queries.cancelled_by_day(first, last, seller=seller),
        returns=queries.returns_by_day(first, last, seller=seller),
        flows=[] if scoped else queries.money_flows(first, last),
        expenses=[] if scoped else queries.expense_flows(first, last),
    )


def figures_by_day(
    uow: UnitOfWork, period: Period, *, seller: UserId | None = None
) -> list[DayFigures]:
    return daily_figures(period.each_day(), inputs_of(uow, period, seller=seller))
