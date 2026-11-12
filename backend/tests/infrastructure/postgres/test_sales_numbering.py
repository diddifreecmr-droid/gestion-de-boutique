"""Critère A8 / ERR-VER-03 de bout en bout : 20 **ventes** concurrentes par `RecordSale`.

`test_concurrency.py` prouve l'allocateur seul ; ici, 20 vendeurs valident en même temps une
vente comptant du même article (même ligne de stock, même séquence `V`). Attendu : numéros
`V-000001` à `V-000020` sans trou ni doublon, aucun conflit renvoyé (réessais internes), un
mouvement « Sortie vente » par vente et un stock final exact.
"""

import threading
from uuid import uuid4

from app.application.ports.pagination import PageRequest
from app.application.sales.checks import SalesCustomerDebt
from app.application.sales.inputs import LineInput, PaymentInput, SaleInput
from app.application.sales.use_cases.record_sale import RecordSale, RecordSaleCommand
from app.application.security.actor import Actor
from app.application.security.policy import Policy
from app.application.shops.ports import PaymentModeRepository
from app.application.stock.ports import StockLevelRepository, StockMovementLog
from app.application.stock.postings import Posting
from app.domain.sales.values import SaleKind
from app.domain.shared.ids import DeviceId, ShopId, UserId
from app.domain.shared.money import Money
from app.domain.shared.roles import Role
from app.domain.shops.payment_mode import PaymentMode, PaymentModeDetails
from app.domain.stock.values import MovementType, SourceRef, SourceType
from tests.contracts.backends.postgres import PostgresContractBackend
from tests.contracts.catalog_data import NOW
from tests.contracts.stock_data import AUTHOR, seed, units
from tests.infrastructure.postgres.concurrent import Task, run_concurrently, unexpected
from tests.infrastructure.postgres.test_sales_concurrency import CLOCK, LEDGER, BarrierFactory

SALES = 20


def test_20_concurrent_sales_are_numbered_without_gap(
    pg: PostgresContractBackend, shop: ShopId
) -> None:
    data = seed(pg, shop)
    with pg.uow(shop) as uow:
        LEDGER.record_entry(uow, Posting(
            article_id=data.article.id, location_id=data.garoua.id, type=MovementType.OPENING,
            quantity=units(SALES + 5), source=SourceRef(SourceType.IMPORT, uuid4()),
            occurred_at=NOW, author_id=AUTHOR, unit_cost=Money(540_000),
        ))  # fmt: skip
        cash = PaymentMode.seed(shop, PaymentModeDetails(name="Espèces", reference_required=False))
        PaymentModeRepository.within(uow).add(cash)
        uow.commit()
    mode = cash.id

    def task(barrier: threading.Barrier) -> str:
        seller = Actor.member(user_id=UserId.new(), device_id=DeviceId.new(), shop_id=shop,
                              role=Role.OWNER)  # fmt: skip
        use_case = RecordSale(
            BarrierFactory(pg, barrier), Policy(CLOCK.now), LEDGER, CLOCK, SalesCustomerDebt()
        )
        sale = SaleInput(
            kind=SaleKind.CASH,
            lines=(LineInput(article_id=data.article.id, quantity=1, unit_price=780_000),),
            location_id=data.garoua.id,
            payments=(PaymentInput(mode_id=mode, amount=780_000),),
        )
        view, _ = use_case.execute(seller, RecordSaleCommand(data=sale))
        return str(view.sale.number)

    tasks: list[Task] = [task] * SALES
    outcomes = run_concurrently(tasks)
    assert unexpected(outcomes) == []  # aucun VERSION_CONFLICT renvoyé au client
    numbers = sorted(str(o.value) for o in outcomes)
    assert numbers == [f"V-{n:06d}" for n in range(1, SALES + 1)]
    with pg.uow(shop) as uow:
        history = StockMovementLog.within(uow).for_article(data.article.id, PageRequest(200))
        level = StockLevelRepository.within(uow).find_level(data.article.id, data.garoua.id)
        uow.rollback()
    assert [m.type for m in history.items].count(MovementType.SALE_OUT) == SALES
    assert level is not None
    assert level.sellable == units(5)
