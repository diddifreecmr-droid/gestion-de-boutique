"""Adaptateur SQL du port de requête `DashboardQueries` (T19, TR-21, specs § 10).

Agrégats calculés à la demande sur des index de période (`reporting_sales.py`,
`reporting_money.py`), sans table de résumés au Lot 1. États lus maintenant :

- total à recevoir = Σ montants initiaux des créances `open` - Σ versements valides de ces
  créances (le reste n'est pas une colonne : la vérité reste les versements, § 5.4) ;
- rappels du jour : index `receivable_reminder (shop_id, status, remind_on)` ;
- demandes de prix en attente : index `price_request (shop_id, status, expires_at)`.
Toutes les requêtes filtrent la boutique du port (specs § 8.3).
"""

from datetime import date, datetime
from typing import Any

import sqlalchemy as sa

from app.application.reporting.ports import (
    DashboardQueries,
    ExpenseFlow,
    MoneyFlow,
    PendingAlerts,
    ReceivablesPosition,
    ReturnsDay,
    SalesDay,
)
from app.domain.receivables.follow_up import ReminderStatus
from app.domain.receivables.installment import InstallmentStatus
from app.domain.receivables.values import ReceivableStatus
from app.domain.sales.error_report import ReportStatus
from app.domain.sales.price_request import PriceRequestStatus
from app.domain.shared.ids import UserId
from app.infrastructure.persistence.sqlalchemy import reporting_money as money
from app.infrastructure.persistence.sqlalchemy import reporting_sales as sales
from app.infrastructure.persistence.sqlalchemy import tables_receivables as rc
from app.infrastructure.persistence.sqlalchemy import tables_sales as t
from app.infrastructure.persistence.sqlalchemy import tables_sales_returns as r
from app.infrastructure.persistence.sqlalchemy.columns import to_db
from app.infrastructure.persistence.sqlalchemy.shop_store import SqlShopStore

R, V, M = rc.receivable.c, rc.installment.c, rc.receivable_reminder.c
_TO_DO = [s.value for s in ReminderStatus if s is not ReminderStatus.DONE]
"""Rappels non faits : liste explicite, servie par l'index `(shop_id, status, remind_on)`."""


class SqlDashboardQueries(SqlShopStore, DashboardQueries):
    table = t.sale

    def sales_by_day(
        self, first_day: date, last_day: date, *, seller: UserId | None = None
    ) -> list[SalesDay]:
        return sales.sales_by_day(self._transaction, self.shop_id, first_day, last_day, seller)

    def cancelled_by_day(
        self, first_day: date, last_day: date, *, seller: UserId | None = None
    ) -> list[SalesDay]:
        return sales.cancelled_by_day(self._transaction, self.shop_id, first_day, last_day, seller)

    def returns_by_day(
        self, first_day: date, last_day: date, *, seller: UserId | None = None
    ) -> list[ReturnsDay]:
        return sales.returns_by_day(self._transaction, self.shop_id, first_day, last_day, seller)

    def money_flows(self, first_day: date, last_day: date) -> list[MoneyFlow]:
        return money.money_flows(self._transaction, self.shop_id, first_day, last_day)

    def expense_flows(self, first_day: date, last_day: date) -> list[ExpenseFlow]:
        return money.expense_flows(self._transaction, self.shop_id, first_day, last_day)

    def _open(self, responsible: UserId | None) -> list[sa.ColumnElement[bool]]:
        where = [R.shop_id == self.shop_id.value, R.status == ReceivableStatus.OPEN.value]
        return (
            where if responsible is None else [*where, R.responsible_seller_id == responsible.value]
        )

    def receivables_position(self, *, responsible: UserId | None = None) -> ReceivablesPosition:
        head = sa.select(
            sales.total(R.initial_amount).label("initial"),
            sa.func.count(sa.distinct(R.customer_id)).label("debtors"),
        ).where(*self._open(responsible))
        paid = (
            sa.select(sales.total(V.amount).label("paid"))
            .select_from(rc.receivable.join(rc.installment, V.receivable_id == R.id))
            .where(*self._open(responsible), V.shop_id == self.shop_id.value)
            .where(V.status == InstallmentStatus.VALID.value)
        )
        found, versed = self._transaction.fetch_one(head), self._transaction.fetch_one(paid)
        if found is None or versed is None:  # un agrégat rend toujours une ligne
            msg = "Agrégat des créances sans ligne"
            raise RuntimeError(msg)
        return ReceivablesPosition(
            total_due=int(found["initial"]) - int(versed["paid"]),
            debtor_count=int(found["debtors"]),
        )

    def reminders_due(self, today: date, *, responsible: UserId | None = None) -> int:
        statement = (
            sa.select(sa.func.count().label("n"))
            .select_from(rc.receivable.join(rc.receivable_reminder, M.receivable_id == R.id))
            .where(*self._open(responsible), M.shop_id == self.shop_id.value)
            .where(M.status.in_(_TO_DO), M.remind_on <= today)
        )
        return self._count(statement)

    def pending_alerts(self, now: datetime) -> PendingAlerts:
        e, p = t.sale_error_report.c, r.price_request.c
        reports = sa.select(sa.func.count().label("n")).where(
            e.shop_id == self.shop_id.value, e.status == ReportStatus.OPEN.value
        )
        requests = sa.select(sa.func.count().label("n")).where(
            p.shop_id == self.shop_id.value,
            p.status == PriceRequestStatus.PENDING.value,
            p.expires_at > to_db(now),
        )
        return PendingAlerts(
            error_reports=self._count(reports), price_requests=self._count(requests)
        )

    def _count(self, statement: sa.Select[Any]) -> int:
        row = self._transaction.fetch_one(statement)
        if row is None:
            msg = "Comptage sans ligne"
            raise RuntimeError(msg)
        return int(row["n"])


SQL_REPORTING_ADAPTERS = (SqlDashboardQueries,)
"""Adaptateurs SQL du module Tableau de bord, à inscrire dans `SQL_REPOSITORIES`."""
