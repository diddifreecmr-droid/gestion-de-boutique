"""Contrat du port de requête `DashboardQueries` (T19) : sommes par journée de Douala, annulations
au jour où elles sont faites (Q-09, frontière 23:00Z), retours et remboursements, portée vendeur,
créances En cours, rappels du jour, alertes en attente, isolation des boutiques.

Rejoué sur l'adaptateur mémoire, sur SQLite (`tests/infrastructure/sqlalchemy`) et sur
PostgreSQL (`--backend=postgres`).
"""

from datetime import timedelta

from app.application.expenses.ports import ExpenseRepository
from app.application.receivables.ports import ReceivableRepository
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
from app.application.sales.ports import ErrorReportRepository, SaleRepository
from app.application.sales.return_ports import PriceRequestRepository, SaleReturnRepository
from app.domain.sales.error_report import ErrorReport
from app.domain.shared.ids import ShopId
from tests.contracts.backends import ContractBackend
from tests.contracts.expense_data import CATEGORY
from tests.contracts.helpers import run_in_uow
from tests.contracts.reporting_data import (
    AFTER,
    BEFORE,
    CASH,
    MTN,
    OTHER_SELLER,
    D,
    at,
    expenses_of,
    sales_book,
)
from tests.contracts.sales_data import SELLER
from tests.contracts.test_sales_returns_contract import ask


def _store(backend: ContractBackend, shop_id: ShopId) -> None:
    book = sales_book(shop_id)

    def add(uow) -> None:  # type: ignore[no-untyped-def]
        for sale in book.sales:
            SaleRepository.within(uow).add(sale)
        SaleReturnRepository.within(uow).add(book.returned)
        for receivable in book.receivables:
            ReceivableRepository.within(uow).add(receivable)
        for expense in expenses_of(shop_id):
            ExpenseRepository.within(uow).add(expense)
        first = book.sales[0]
        report = ErrorReport.report(
            shop_id, first.id, str(first.number), "mauvais prix", performer=SELLER, now=at(10, 9)
        )
        ErrorReportRepository.within(uow).add(report)
        PriceRequestRepository.within(uow).add(ask(shop_id))

    run_in_uow(backend, shop_id, add)


def test_sales_cancellations_and_returns_by_day(
    backend: ContractBackend, shop_a: ShopId, shop_b: ShopId
) -> None:
    _store(backend, shop_a)
    with backend.uow(shop_a) as uow:
        q = DashboardQueries.within(uow)
        assert q.sales_by_day(BEFORE, AFTER) == [
            SalesDay(day=BEFORE, count=1, total=790_000, margin=240_000, margin_wac=260_000),
            SalesDay(day=D, count=3, total=2_180_000, margin=430_000, margin_wac=490_000,
                     without_cost=1, without_wac=1),
        ]  # fmt: skip
        assert q.sales_by_day(D, D, seller=SELLER.user_id) == [
            SalesDay(day=D, count=2, total=1_480_000, margin=280_000, margin_wac=320_000,
                     without_cost=1, without_wac=1),
        ]  # fmt: skip
        assert q.cancelled_by_day(BEFORE, AFTER) == [
            SalesDay(day=D, count=1, total=790_000, margin=240_000, margin_wac=260_000),
            SalesDay(day=AFTER, count=1, total=600_000, margin=50_000, margin_wac=70_000),
        ]
        assert q.cancelled_by_day(D, D, seller=OTHER_SELLER) == []
        returned = ReturnsDay(day=D, count=1, amount=780_000, margin=230_000, margin_wac=250_000)
        assert q.returns_by_day(BEFORE, AFTER) == [returned]
        assert q.returns_by_day(D, D, seller=SELLER.user_id) == [returned]
        assert q.returns_by_day(D, D, seller=OTHER_SELLER) == []
        assert q.returns_by_day(AFTER, AFTER) == []
    with backend.uow(shop_b) as uow:
        q = DashboardQueries.within(uow)
        assert q.sales_by_day(BEFORE, AFTER) == []
        assert q.cancelled_by_day(BEFORE, AFTER) == []
        assert q.returns_by_day(BEFORE, AFTER) == []


def test_money_and_expense_flows(backend: ContractBackend, shop_a: ShopId, shop_b: ShopId) -> None:
    _store(backend, shop_a)
    with backend.uow(shop_a) as uow:
        q = DashboardQueries.within(uow)
        flows = {
            (f.day, f.kind, f.mode_id): (f.amount, f.count) for f in q.money_flows(BEFORE, AFTER)
        }
        assert flows == {
            (BEFORE, FlowKind.SALE_DEPOSIT, MTN): (90_000, 1),
            (D, FlowKind.SALE_CASH, CASH): (1_480_000, 2),
            (D, FlowKind.SALE_DEPOSIT, MTN): (200_000, 1),
            (D, FlowKind.SALE_CANCELLED, MTN): (90_000, 1),
            (D, FlowKind.INSTALLMENT, CASH): (70_000, 2),
            (D, FlowKind.REFUND, CASH): (780_000, 1),
            (AFTER, FlowKind.SALE_CANCELLED, CASH): (600_000, 1),
            (AFTER, FlowKind.INSTALLMENT_CANCELLED, CASH): (20_000, 1),
        }
        only_d = q.money_flows(D, D)
        assert {f.day for f in only_d} == {D}
        assert sum(f.signed for f in only_d) == 1_480_000 + 200_000 - 90_000 + 70_000 - 780_000
        assert q.expense_flows(BEFORE, AFTER) == [
            ExpenseFlow(day=D, category_id=CATEGORY, amount=3_000, count=2, cancelled=False),
            ExpenseFlow(day=AFTER, category_id=CATEGORY, amount=2_000, count=1, cancelled=True),
        ]
        assert q.expense_flows(D, D)[0].signed == 3_000
    with backend.uow(shop_b) as uow:
        assert DashboardQueries.within(uow).money_flows(BEFORE, AFTER) == []
        assert DashboardQueries.within(uow).expense_flows(BEFORE, AFTER) == []
    assert MoneyFlow(day=D, kind=FlowKind.REFUND, mode_id=CASH, amount=5, count=1).signed == -5


def test_receivables_reminders_and_pending_alerts(
    backend: ContractBackend, shop_a: ShopId, shop_b: ShopId
) -> None:
    _store(backend, shop_a)
    with backend.uow(shop_a) as uow:
        q = DashboardQueries.within(uow)
        assert q.receivables_position() == ReceivablesPosition(total_due=550_000, debtor_count=2)
        mine = q.receivables_position(responsible=SELLER.user_id)
        assert mine == ReceivablesPosition(total_due=250_000, debtor_count=1)
        assert q.receivables_position(responsible=OTHER_SELLER).total_due == 0
        assert q.reminders_due(D) == 1
        assert q.reminders_due(D - timedelta(days=1)) == 0
        assert q.reminders_due(D + timedelta(days=5)) == 2
        assert q.reminders_due(D, responsible=SELLER.user_id) == 1
        assert q.reminders_due(D, responsible=OTHER_SELLER) == 0
        requested = ask(shop_a).requested_at
        assert q.pending_alerts(requested) == PendingAlerts(error_reports=1, price_requests=1)
        late = requested + timedelta(minutes=30)
        assert q.pending_alerts(late) == PendingAlerts(error_reports=1, price_requests=0)
    with backend.uow(shop_b) as uow:
        q = DashboardQueries.within(uow)
        assert q.receivables_position() == ReceivablesPosition(total_due=0, debtor_count=0)
        assert q.reminders_due(D) == 0
        assert q.pending_alerts(at(10, 9)) == PendingAlerts(error_reports=0, price_requests=0)
