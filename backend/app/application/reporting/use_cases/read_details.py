"""UC-TDB-04 — Ouvrir le détail d'un chiffre (propriétaire, `DASHBOARD_READ`).

Même période que le tableau de bord (`periods.resolve_period`) ; les listes et leurs règles
sont dans `reporting/details.py`. Le total renvoyé est le chiffre du tableau de bord.
"""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWork, UnitOfWorkFactory
from app.application.receivables.ports import ReceivableRepository
from app.application.reporting.details import (
    DetailLine,
    DetailMetric,
    LineKind,
    by_category,
    by_mode,
    receivable_lines,
    sales_lines,
)
from app.application.reporting.periods import Period, PeriodKind, resolve_period
from app.application.reporting.ports import DashboardQueries
from app.application.reporting.stock_figures import low_stock_in
from app.application.sales.ports import CustomerRepository, SaleRepository
from app.application.sales.return_ports import SaleReturnRepository
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop
from app.application.shops.ports import ExpenseCategoryRepository, PaymentModeRepository


@dataclass(frozen=True, slots=True, kw_only=True)
class DetailReport:
    metric: DetailMetric
    period: Period
    total: int
    lines: list[DetailLine]


def _sales(uow: UnitOfWork, period: Period) -> list[DetailLine]:
    sales = SaleRepository.within(uow)
    first, last = period.first_day, period.last_day
    return sales_lines(
        sales.list_between(first, last),
        sales.cancelled_between(first, last),
        SaleReturnRepository.within(uow).between(first, last),
    )


def _payments(uow: UnitOfWork, period: Period) -> list[DetailLine]:
    names = {m.id: m.name for m in PaymentModeRepository.within(uow).list_all()}
    flows = DashboardQueries.within(uow).money_flows(period.first_day, period.last_day)
    return by_mode(flows, names)


def _expenses(uow: UnitOfWork, period: Period) -> list[DetailLine]:
    names = {c.id: c.name for c in ExpenseCategoryRepository.within(uow).list_all()}
    flows = DashboardQueries.within(uow).expense_flows(period.first_day, period.last_day)
    return by_category(flows, names)


def _receivables(uow: UnitOfWork, _period: Period) -> list[DetailLine]:
    open_ = [r for r in ReceivableRepository.within(uow).list_all() if r.counts_as_due]
    customers = CustomerRepository.within(uow)
    names: dict[UUID, str] = {}
    for r in open_:
        if r.customer_id.value not in names:
            names[r.customer_id.value] = customers.get(r.customer_id).name
    return receivable_lines(open_, names)


def _low_stock(uow: UnitOfWork, _period: Period) -> list[DetailLine]:
    return [
        DetailLine(
            kind=LineKind.ARTICLE,
            id=low.article.id.value,
            label=low.article.display_name,
            count=1,
            quantity=low.quantity,
            threshold=low.threshold,
        )
        for low in low_stock_in(uow)
    ]


_BUILDERS = {
    DetailMetric.SALES: _sales,
    DetailMetric.PAYMENTS: _payments,
    DetailMetric.EXPENSES: _expenses,
    DetailMetric.RECEIVABLES: _receivables,
    DetailMetric.LOW_STOCK: _low_stock,
}


class ReadDashboardDetail:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock

    def execute(
        self,
        actor: Actor,
        metric: DetailMetric,
        kind: PeriodKind = PeriodKind.TODAY,
        first_day: date | None = None,
        last_day: date | None = None,
    ) -> DetailReport:
        self._policy.require(actor, Permission.DASHBOARD_READ)
        period = resolve_period(kind, self._clock.today(), first_day, last_day)
        with self._uow_factory(actor_shop(actor)) as uow:
            lines = _BUILDERS[metric](uow, period)
        count_only = metric is DetailMetric.LOW_STOCK
        total = len(lines) if count_only else sum(line.amount or 0 for line in lines)
        return DetailReport(metric=metric, period=period, total=total, lines=lines)
