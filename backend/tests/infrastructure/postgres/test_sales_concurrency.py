"""Ventes sous transactions réellement concurrentes sur PostgreSQL (RG-M01, ERR-STK-05).

Deux ventes simultanées **du même châssis** (stock suffisant) : une seule réussit ; l'autre,
rejouée par `with_sale_retry`, reçoit `DUPLICATE` avec le numéro de la vente gagnante. Une
seule « Sortie vente », un seul châssis réservé.
"""

import threading
from uuid import uuid4

from app.application.ports.pagination import PageRequest
from app.application.sales.checks import SalesCustomerDebt
from app.application.sales.inputs import CustomerInput, LineInput, SaleInput
from app.application.sales.ports import ChassisClaimRepository
from app.application.sales.use_cases.record_sale import RecordSale, RecordSaleCommand
from app.application.sales.views import SaleView
from app.application.security.actor import Actor
from app.application.security.policy import Policy
from app.application.stock.ledger import StockLedger
from app.application.stock.ports import StockMovementLog
from app.application.stock.postings import Posting
from app.domain.sales.errors import ChassisAlreadySold
from app.domain.sales.lines import SoldDetail
from app.domain.sales.values import SaleKind
from app.domain.shared.ids import DeviceId, ShopId, UserId
from app.domain.shared.money import Money
from app.domain.shared.roles import Role
from app.domain.stock.values import MovementType, SourceRef, SourceType
from app.infrastructure.persistence.memory.clock import FixedClock
from tests.contracts.backends.postgres import PostgresContractBackend
from tests.contracts.catalog_data import NOW
from tests.contracts.stock_data import AUTHOR, seed, units
from tests.infrastructure.postgres.concurrent import Task, run_concurrently, unexpected

CLOCK = FixedClock(NOW)
LEDGER = StockLedger(CLOCK)


class BarrierFactory:
    """Fabrique d'unités : la première de chaque tâche attend l'autre avant d'écrire."""

    def __init__(self, pg: PostgresContractBackend, barrier: threading.Barrier) -> None:
        self._pg, self._barrier, self._first = pg, barrier, True

    def __call__(self, shop_id: ShopId):  # type: ignore[no-untyped-def]
        if self._first:
            self._first = False
            self._barrier.wait()
        return self._pg.uow(shop_id)


def test_same_chassis_sold_twice_concurrently_one_wins(
    pg: PostgresContractBackend, shop: ShopId
) -> None:
    data = seed(pg, shop)
    with pg.uow(shop) as uow:
        LEDGER.record_entry(
            uow,
            Posting(
                article_id=data.article.id,
                location_id=data.garoua.id,
                type=MovementType.OPENING,
                quantity=units(2),
                source=SourceRef(SourceType.IMPORT, uuid4()),
                occurred_at=NOW,
                author_id=AUTHOR,
                unit_cost=Money(540_000),
            ),
        )
        uow.commit()
    owner = Actor.member(
        user_id=UserId.new(), device_id=DeviceId.new(), shop_id=shop, role=Role.OWNER
    )

    def task(phone: str) -> Task:
        def run(barrier: threading.Barrier) -> SaleView:
            use_case = RecordSale(
                BarrierFactory(pg, barrier), Policy(CLOCK.now), LEDGER, CLOCK, SalesCustomerDebt()
            )
            line = LineInput(
                article_id=data.article.id,
                quantity=1,
                unit_price=780_000,
                details=(SoldDetail(chassis_number="LBX123"),),
            )
            sale = SaleInput(
                kind=SaleKind.CREDIT,
                lines=(line,),
                location_id=data.garoua.id,
                customer=CustomerInput(name="Client", phone=phone),
            )
            view, _ = use_case.execute(owner, RecordSaleCommand(data=sale))
            return view

        return run

    outcomes = run_concurrently([task("690000001"), task("690000002")])
    assert unexpected(outcomes, ChassisAlreadySold) == []
    assert sorted(o.error is None for o in outcomes) == [False, True]
    loser = next(o.error for o in outcomes if o.error is not None)
    assert isinstance(loser, ChassisAlreadySold)
    assert loser.details["sale_number"] in ("V-000001", "V-000002")
    with pg.uow(shop) as uow:
        history = StockMovementLog.within(uow).for_article(data.article.id, PageRequest())
        held = ChassisClaimRepository.within(uow).find_active("LBX123")
    assert [m.type for m in history.items].count(MovementType.SALE_OUT) == 1
    assert held is not None
