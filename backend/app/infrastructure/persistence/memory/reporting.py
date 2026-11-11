"""Adaptateur mémoire du port de requête `DashboardQueries` (T19, TR-21).

Lit les agrégats des autres modules (ventes, retours, créances, dépenses, signalements, demandes
de prix) dans la transaction, sans les suivre (lecture seule). Même sémantique que l'adaptateur
SQL (`tests/contracts/test_reporting_contract.py`) : journée de rattachement de chaque somme
décrite dans `application/reporting/ports.py`.
"""

import copy
from collections import defaultdict
from collections.abc import Callable, Iterable
from datetime import date, datetime
from typing import Any, cast

from app.application.reporting.ports import (
    DashboardQueries,
    ExpenseFlow,
    FlowKind,
    MoneyFlow,
    PendingAlerts,
    ReceivablesPosition,
    ReturnsDay,
    SalesDay,
)
from app.domain.expenses.expense import Expense
from app.domain.receivables.follow_up import ReminderStatus
from app.domain.receivables.receivable import Receivable
from app.domain.sales.error_report import ErrorReport, ReportStatus
from app.domain.sales.price_request import PriceRequest, PriceRequestStatus
from app.domain.sales.sale import Sale
from app.domain.sales.sale_return import SaleReturn
from app.domain.sales.values import SaleKind
from app.domain.shared.business_day import business_date
from app.domain.shared.ids import UserId
from app.infrastructure.persistence.memory.shop_store import MemoryShopStore

type FlowKey = tuple[date, FlowKind, Any]


def _sales_day(day: date, sales: list[Sale]) -> SalesDay:
    lines = [line for sale in sales for line in sale.content.lines]
    return SalesDay(
        day=day,
        count=len(sales),
        total=sum(s.total.amount for s in sales),
        margin=sum(m.amount for line in lines if (m := line.margin) is not None),
        margin_wac=sum(m.amount for line in lines if (m := line.margin_wac) is not None),
        without_cost=sum(1 for line in lines if line.margin is None),
        without_wac=sum(1 for line in lines if line.margin_wac is None),
    )


def _cancelled_on(sale: Sale) -> date:
    if sale.cancellation is None:  # filtré par l'appelant : défense en profondeur
        msg = f"Vente {sale.number} sans annulation"
        raise RuntimeError(msg)
    return business_date(sale.cancellation.at)


def _by_key[K](item: tuple[K, list[int]]) -> tuple[str, ...]:
    return tuple(str(part) for part in cast(tuple[object, ...], item[0]))


def _grouped[T](items: Iterable[T], day_of: Callable[[T], date]) -> dict[date, list[T]]:
    groups: dict[date, list[T]] = defaultdict(list)
    for item in items:
        groups[day_of(item)].append(item)
    return dict(sorted(groups.items()))


def _flows(sums: dict[FlowKey, list[int]]) -> list[MoneyFlow]:
    return [
        MoneyFlow(day=day, kind=kind, mode_id=mode, amount=sum(v), count=len(v))
        for (day, kind, mode), v in sorted(sums.items(), key=_by_key)
    ]


class MemoryDashboardQueries(MemoryShopStore, DashboardQueries):
    table = "sales"

    def _all[T](self, table: str, _kind: type[T]) -> list[T]:
        # Lignes écrites par les dépôts mémoire des modules (charge utile = l'agrégat).
        return [cast(T, copy.deepcopy(row.payload)) for row in self._transaction.rows(table)]

    def _sales(self, seller: UserId | None) -> list[Sale]:
        sales = self._all("sales", Sale)
        return [s for s in sales if seller is None or s.seller_id == seller]

    def sales_by_day(
        self, first_day: date, last_day: date, *, seller: UserId | None = None
    ) -> list[SalesDay]:
        dated = [s for s in self._sales(seller) if first_day <= s.content.sold_on <= last_day]
        return [_sales_day(d, g) for d, g in _grouped(dated, lambda s: s.content.sold_on).items()]

    def cancelled_by_day(
        self, first_day: date, last_day: date, *, seller: UserId | None = None
    ) -> list[SalesDay]:
        cancelled = [s for s in self._sales(seller) if s.cancellation is not None]
        groups = _grouped(cancelled, _cancelled_on)
        return [_sales_day(d, g) for d, g in groups.items() if first_day <= d <= last_day]

    def returns_by_day(
        self, first_day: date, last_day: date, *, seller: UserId | None = None
    ) -> list[ReturnsDay]:
        mine = {s.id for s in self._sales(seller)}
        returns = [
            r
            for r in self._all("sale_returns", SaleReturn)
            if r.sale_id in mine and first_day <= r.returned_on <= last_day
        ]
        return [
            ReturnsDay(
                day=day,
                count=len(group),
                amount=sum(r.amount.amount for r in group),
                margin=sum(m.amount for r in group if (m := r.margin) is not None),
                margin_wac=sum(m.amount for r in group if (m := r.margin_wac) is not None),
                without_cost=sum(1 for r in group if r.margin is None),
            )
            for day, group in _grouped(returns, lambda r: r.returned_on).items()
        ]

    def money_flows(self, first_day: date, last_day: date) -> list[MoneyFlow]:
        sums: dict[FlowKey, list[int]] = defaultdict(list)

        def add(day: date, kind: FlowKind, mode: object, amount: int) -> None:
            if first_day <= day <= last_day:
                sums[(day, kind, mode)].append(amount)

        for sale in self._sales(None):
            paid = FlowKind.SALE_CASH if sale.kind is SaleKind.CASH else FlowKind.SALE_DEPOSIT
            for payment in sale.content.payments:
                add(sale.content.sold_on, paid, payment.mode_id, payment.amount.amount)
                if sale.cancellation is not None:
                    day = business_date(sale.cancellation.at)
                    add(day, FlowKind.SALE_CANCELLED, payment.mode_id, payment.amount.amount)
        for receivable in self._all("receivables", Receivable):
            for i in receivable.installments:
                add(i.paid_on, FlowKind.INSTALLMENT, i.mode_id, i.amount.amount)
                if i.cancellation is not None:
                    day = business_date(i.cancellation.at)
                    add(day, FlowKind.INSTALLMENT_CANCELLED, i.mode_id, i.amount.amount)
        for r in self._all("sale_returns", SaleReturn):
            if r.refund is not None:
                add(r.refund.refunded_on, FlowKind.REFUND, r.refund.mode_id, r.refund.amount.amount)
        return _flows(sums)

    def expense_flows(self, first_day: date, last_day: date) -> list[ExpenseFlow]:
        sums: dict[tuple[date, bool, Any], list[int]] = defaultdict(list)
        for expense in self._all("expenses", Expense):
            key = expense.details.category_id
            sums[(expense.details.spent_on, False, key)].append(expense.details.amount)
            if expense.cancellation is not None:
                day = business_date(expense.cancellation.at)
                sums[(day, True, key)].append(expense.details.amount)
        return [
            ExpenseFlow(day=d, category_id=c, amount=sum(v), count=len(v), cancelled=cancelled)
            for (d, cancelled, c), v in sorted(sums.items(), key=_by_key)
            if first_day <= d <= last_day
        ]

    def _open(self, responsible: UserId | None) -> list[Receivable]:
        found = [r for r in self._all("receivables", Receivable) if r.counts_as_due]
        return [r for r in found if responsible is None or r.responsible_seller_id == responsible]

    def receivables_position(self, *, responsible: UserId | None = None) -> ReceivablesPosition:
        due = self._open(responsible)
        return ReceivablesPosition(
            total_due=sum(r.remaining.amount for r in due),
            debtor_count=len({r.customer_id for r in due}),
        )

    def reminders_due(self, today: date, *, responsible: UserId | None = None) -> int:
        return sum(
            1
            for r in self._open(responsible)
            for m in r.reminders
            if m.status is not ReminderStatus.DONE and m.remind_on <= today
        )

    def pending_alerts(self, now: datetime) -> PendingAlerts:
        reports = self._all("sale_error_reports", ErrorReport)
        requests = self._all("price_requests", PriceRequest)
        return PendingAlerts(
            error_reports=sum(1 for r in reports if r.status is ReportStatus.OPEN),
            price_requests=sum(
                1 for r in requests if r.status_at(now) is PriceRequestStatus.PENDING
            ),
        )


MEMORY_REPORTING_ADAPTERS = (MemoryDashboardQueries,)
