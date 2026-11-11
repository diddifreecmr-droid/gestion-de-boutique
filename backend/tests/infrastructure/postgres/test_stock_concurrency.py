"""Stock sous transactions réellement concurrentes sur PostgreSQL (ERR-STK-05, TR-13, D6).

Deux sorties simultanées de la dernière unité d'un lieu : la seconde `UPDATE` attend le verrou
de ligne de la première puis ne trouve plus la version lue (`VersionConflict`) ; rejouée par
`with_stock_retry`, elle relit le stock à 0 et reçoit `STOCK_INSUFFICIENT`. Jamais deux
succès, jamais de stock négatif.
"""

import threading
from collections.abc import Callable
from uuid import uuid4

from app.application.ports.pagination import PageRequest
from app.application.stock.ledger import StockLedger
from app.application.stock.ports import StockLevelRepository, StockMovementLog
from app.application.stock.postings import Posting
from app.application.stock.retry import with_stock_retry
from app.domain.shared.errors import VersionConflict
from app.domain.shared.ids import ShopId
from app.domain.stock.errors import StockInsufficient
from app.domain.stock.movement import StockMovement
from app.domain.stock.values import MovementType, SourceRef, SourceType
from app.infrastructure.persistence.memory.clock import FixedClock
from tests.contracts.backends.postgres import PostgresContractBackend
from tests.contracts.catalog_data import NOW
from tests.contracts.stock_data import AUTHOR, Seeded, seed, units
from tests.infrastructure.postgres.concurrent import Task, run_concurrently, unexpected

LEDGER = StockLedger(FixedClock(NOW))


def posting(data: Seeded, kind: MovementType) -> Posting:
    return Posting(
        article_id=data.article.id,
        location_id=data.garoua.id,
        type=kind,
        quantity=units(1),
        source=SourceRef(SourceType.SALE, uuid4()),
        occurred_at=NOW,
        author_id=AUTHOR,
    )


def task(
    pg: PostgresContractBackend, shop: ShopId, data: Seeded, kind: MovementType, *, retry: bool
) -> Task:
    def run(barrier: threading.Barrier) -> StockMovement:
        waiting = [True]

        def attempt() -> StockMovement:
            with pg.uow(shop) as uow:
                if waiting[0]:  # les deux transactions lisent avant la première écriture
                    waiting[0] = False
                    StockLevelRepository.within(uow).find_level(data.article.id, data.garoua.id)
                    barrier.wait()
                post: Callable[..., StockMovement] = (
                    LEDGER.record_exit if kind is MovementType.SALE_OUT else LEDGER.record_entry
                )
                movement = post(uow, posting(data, kind))
                uow.commit()
            return movement

        return with_stock_retry(attempt) if retry else attempt()

    return run


def stock_in(pg: PostgresContractBackend, shop: ShopId, data: Seeded) -> None:
    with pg.uow(shop) as uow:
        LEDGER.record_entry(uow, posting(data, MovementType.CUSTOMER_RETURN))
        uow.commit()


def final_state(pg: PostgresContractBackend, shop: ShopId, data: Seeded) -> tuple[str, int]:
    with pg.uow(shop) as uow:
        level = StockLevelRepository.within(uow).find_level(data.article.id, data.garoua.id)
        history = StockMovementLog.within(uow).for_article(data.article.id, PageRequest())
    assert level is not None
    return str(level.sellable), len(history.items)


def test_two_exits_of_last_unit_one_wins(pg: PostgresContractBackend, shop: ShopId) -> None:
    data = seed(pg, shop)
    stock_in(pg, shop, data)
    outcomes = run_concurrently([task(pg, shop, data, MovementType.SALE_OUT, retry=True)] * 2)
    assert unexpected(outcomes, StockInsufficient) == []
    assert sorted(o.error is None for o in outcomes) == [False, True]
    assert final_state(pg, shop, data) == ("0", 2)  # une entrée + une seule sortie


def test_without_retry_the_loser_gets_a_version_conflict(
    pg: PostgresContractBackend, shop: ShopId
) -> None:
    data = seed(pg, shop)
    stock_in(pg, shop, data)
    stock_in(pg, shop, data)
    outcomes = run_concurrently([task(pg, shop, data, MovementType.SALE_OUT, retry=False)] * 2)
    assert unexpected(outcomes, VersionConflict) == []
    assert sorted(o.error is None for o in outcomes) == [False, True]
    assert final_state(pg, shop, data) == ("1", 3)


def test_two_first_entries_create_one_projection(pg: PostgresContractBackend, shop: ShopId) -> None:
    data = seed(pg, shop)
    kind = MovementType.CUSTOMER_RETURN
    outcomes = run_concurrently([task(pg, shop, data, kind, retry=True)] * 2)
    assert unexpected(outcomes) == []
    assert final_state(pg, shop, data) == ("2", 2)
