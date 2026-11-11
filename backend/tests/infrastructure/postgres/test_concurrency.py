"""PostgreSQL sous transactions réellement concurrentes (specs A8, verrou optimiste)."""

import threading

import pytest

from app.domain.shared.doc_number import DocType
from app.domain.shared.errors import Duplicate, VersionConflict
from app.domain.shared.ids import ShopId
from tests.contracts.backends.postgres import PostgresContractBackend
from tests.contracts.helpers import committed_widget, read_widget, widgets
from tests.contracts.widget import Widget
from tests.infrastructure.postgres.concurrent import Task, run_concurrently, unexpected
from tests.infrastructure.sqlalchemy.test_migrations import constraint_drift, schema_drift

SALES = 20


def sale(pg: PostgresContractBackend, shop: ShopId, doc_type: DocType, *, keep: bool) -> Task:
    def task(barrier: threading.Barrier) -> int | None:
        with pg.uow(shop) as uow:
            barrier.wait()  # toutes les transactions sont ouvertes avant la première attribution
            number = uow.numbering.next(doc_type)
            if not keep:
                uow.rollback()  # vente abandonnée : son numéro revient à la suivante
                return None
            uow.commit()
        return number.sequence

    return task


def test_20_concurrent_sales_get_continuous_gapless_numbers(
    pg: PostgresContractBackend, shop: ShopId
) -> None:
    outcomes = run_concurrently([sale(pg, shop, DocType.SALE, keep=True)] * SALES)
    assert unexpected(outcomes) == []
    assert sorted(int(str(o.value)) for o in outcomes) == list(range(1, SALES + 1))
    with pg.uow(shop) as uow:
        assert str(uow.numbering.next(DocType.SALE)) == "V-000021"
        uow.rollback()


def test_concurrent_rollbacks_leave_no_gap(pg: PostgresContractBackend, shop: ShopId) -> None:
    tasks = [sale(pg, shop, DocType.RECEIPT, keep=i % 3 != 0) for i in range(SALES)]
    outcomes = run_concurrently(tasks)
    assert unexpected(outcomes) == []
    committed = sorted(o.value for o in outcomes if isinstance(o.value, int))
    assert committed == list(range(1, len(committed) + 1))
    assert len(committed) == SALES - len(range(0, SALES, 3))


def test_concurrent_updates_one_wins_the_other_conflicts(
    pg: PostgresContractBackend, shop: ShopId
) -> None:
    widget = committed_widget(pg, shop, "v1")

    def rename(label: str) -> Task:
        def task(barrier: threading.Barrier) -> str:
            with pg.uow(shop) as uow:
                loaded = widgets(uow).get(widget.id)
                barrier.wait()  # les deux ont lu la version 1
                loaded.rename(label)
                widgets(uow).update(loaded)
                uow.commit()
            return label

        return task

    outcomes = run_concurrently([rename("premier"), rename("second")])
    assert unexpected(outcomes, VersionConflict) == []
    winners = [o.value for o in outcomes if o.error is None]
    assert len(winners) == 1
    stored = read_widget(pg, shop, widget)
    assert (stored.label, stored.version) == (winners[0], 2)


@pytest.mark.parametrize("clash", ["code", "id"])
def test_concurrent_inserts_one_wins_the_other_is_a_duplicate(
    pg: PostgresContractBackend, shop: ShopId, clash: str
) -> None:
    first = Widget.create(shop, "a", code="CH-1")
    rival = (
        Widget.create(shop, "b", code="CH-1") if clash == "code" else Widget(first.id, shop, "b")
    )

    def insert(widget: Widget) -> Task:
        def task(barrier: threading.Barrier) -> None:
            with pg.uow(shop) as uow:
                barrier.wait()
                widgets(uow).add(widget)
                uow.commit()

        return task

    outcomes = run_concurrently([insert(first), insert(rival)])
    assert unexpected(outcomes, Duplicate) == []
    duplicates = [o.error for o in outcomes if isinstance(o.error, Duplicate)]
    assert len(duplicates) == 1
    assert duplicates[0].details["constraint"] == ("widget_code" if clash == "code" else "id")


def test_migrations_match_declared_tables_on_postgres(pg: PostgresContractBackend) -> None:
    assert schema_drift(pg.engine) == []
    assert constraint_drift(pg.engine) == {}
