"""Chaque agrégat du tableau de bord passe par un index de période (specs § 10, T19).

Sur un volume réaliste (`reporting_volume.py`, ~3 ans d'activité, statistiques à jour), les
requêtes réellement émises par l'adaptateur SQL sont capturées puis expliquées par PostgreSQL :
aucun balayage séquentiel, et chaque index de période attendu sert au moins une requête.
"""

from datetime import UTC, date, datetime
from typing import Any

import sqlalchemy as sa

from app.application.reporting.ports import DashboardQueries
from app.domain.shared.ids import ShopId, UserId
from tests.contracts.backends.postgres import PostgresContractBackend
from tests.infrastructure.postgres.reporting_volume import SELLERS, seed_volume

PERIOD_INDEXES = {
    "sale_shop_date_idx",
    "sale_shop_seller_idx",
    "sale_shop_cancelled_idx",
    "sale_return_day_idx",
    "sale_return_refund_day_idx",
    "installment_shop_paid_on_idx",
    "installment_shop_cancelled_idx",
    "expense_shop_spent_on_idx",
    "expense_shop_cancelled_idx",
    "receivable_reminder_due_idx",
    "price_request_status_idx",
}


class Recording:
    """Transaction SQL réelle dont on garde chaque requête de lecture."""

    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.statements: list[sa.Select[Any]] = []

    def fetch_all(self, statement: sa.Select[Any]) -> list[sa.RowMapping]:
        self.statements.append(statement)
        rows: list[sa.RowMapping] = self.inner.fetch_all(statement)
        return rows

    def fetch_one(self, statement: sa.Select[Any]) -> sa.RowMapping | None:
        self.statements.append(statement)
        row: sa.RowMapping | None = self.inner.fetch_one(statement)
        return row


def plan_of(connection: sa.Connection, statement: sa.Select[Any]) -> str:
    compiled = statement.compile(
        dialect=connection.dialect, compile_kwargs={"render_postcompile": True}
    )
    rows = connection.exec_driver_sql(f"EXPLAIN {compiled.string}", compiled.params)
    return "\n".join(str(row[0]) for row in rows)


def test_every_dashboard_aggregate_uses_an_index(pg: PostgresContractBackend, shop: ShopId) -> None:
    seed_volume(pg.engine, shop)
    first, last = date(2025, 3, 1), date(2025, 3, 31)
    with pg.uow(shop) as uow:
        queries = DashboardQueries.within(uow)
        recording = Recording(queries._transaction)  # type: ignore[attr-defined]
        queries._transaction = recording  # type: ignore[attr-defined]
        queries.sales_by_day(first, last)
        queries.sales_by_day(first, last, seller=UserId(SELLERS[0]))
        queries.cancelled_by_day(first, last)
        queries.returns_by_day(first, last, seller=UserId(SELLERS[0]))
        queries.money_flows(first, last)
        queries.expense_flows(first, last)
        queries.receivables_position()
        queries.reminders_due(last)
        queries.pending_alerts(datetime(2025, 3, 15, 9, 10, tzinfo=UTC))
    assert len(recording.statements) == 19
    with pg.engine.connect() as connection:
        # Petites tables enfants : sans cela, une jointure par hachage les lirait en entier
        # (bon plan à ce volume) ; on vérifie qu'un chemin indexé existe pour chaque lecture.
        connection.exec_driver_sql("SET enable_seqscan = off")
        plans = [plan_of(connection, statement) for statement in recording.statements]
    scans = [plan for plan in plans if "Seq Scan" in plan]
    assert scans == []
    used = {name for name in PERIOD_INDEXES if any(name in plan for plan in plans)}
    assert used == PERIOD_INDEXES
