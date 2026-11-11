"""Contrat du grand livre de bout en bout sur chaque adaptateur (RG-T16 : projection = somme
des mouvements après une séquence aléatoire d'entrées et de sorties ; RG-T17 : jamais négatif)."""

import random
from datetime import timedelta
from uuid import uuid4

from app.application.ports.pagination import PageRequest
from app.application.stock.ledger import StockLedger
from app.application.stock.ports import StockLevelRepository, StockMovementLog
from app.application.stock.postings import Posting
from app.domain.shared.ids import ShopId
from app.domain.stock.errors import StockInsufficient
from app.domain.stock.values import MovementType, SourceRef, SourceType
from app.infrastructure.persistence.memory.clock import FixedClock
from tests.contracts.backends import ContractBackend
from tests.contracts.catalog_data import NOW
from tests.contracts.stock_data import AUTHOR, seed, units


def test_ledger_projection_is_sum_of_movements(backend: ContractBackend, shop_a: ShopId) -> None:
    data = seed(backend, shop_a)
    ledger, rng = StockLedger(FixedClock(NOW)), random.Random(14)
    expected = 0
    for step in range(25):
        quantity = rng.randint(1, 4)
        entering = rng.random() < 0.55
        posting = Posting(
            article_id=data.article.id,
            location_id=data.garoua.id,
            type=MovementType.CUSTOMER_RETURN if entering else MovementType.SALE_OUT,
            quantity=units(quantity),
            source=SourceRef(SourceType.SALE, uuid4()),
            occurred_at=NOW + timedelta(minutes=step),
            author_id=AUTHOR,
        )
        try:
            with backend.uow(shop_a) as uow:
                post = ledger.record_entry if entering else ledger.record_exit
                post(uow, posting)
                uow.commit()
            expected += quantity if entering else -quantity
        except StockInsufficient:
            assert not entering
            assert expected < quantity
    with backend.uow(shop_a) as uow:
        level = StockLevelRepository.within(uow).find_level(data.article.id, data.garoua.id)
        history = StockMovementLog.within(uow).for_article(data.article.id, PageRequest(200))
    assert level is not None
    assert level.sellable.value == expected == sum(m.quantity.value for m in history.items)
    assert all(m.balance_after.value >= 0 for m in history.items)  # jamais négatif en ligne
