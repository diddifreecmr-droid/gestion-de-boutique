"""Contrat du module Achats (T15) : aller-retour, unicités, isolation, verrou, numérotation `A-`,
liste par période, et Costing sur le grand livre de l'adaptateur (rejeu Q-02 : 515 000).

Rejoué sur l'adaptateur mémoire, sur SQLite (`tests/infrastructure/sqlalchemy`) et sur
PostgreSQL (`--backend=postgres`).
"""

from datetime import date, timedelta
from functools import partial
from uuid import uuid4

import pytest

from app.application.catalog.ports import ArticleRepository
from app.application.ports.uow import UnitOfWork
from app.application.purchasing.costs import refresh_costs, replay_article
from app.application.purchasing.entries import quantity_left
from app.application.purchasing.ports import PurchaseRepository, SupplierRepository
from app.application.stock.ledger import StockLedger
from app.application.stock.postings import Posting
from app.domain.purchasing.payment_rules import add_payment
from app.domain.shared.doc_number import DocType
from app.domain.shared.errors import Duplicate, NotFound, VersionConflict
from app.domain.shared.ids import ShopId
from app.domain.shared.money import Money
from app.domain.stock.values import MovementType, SourceRef, SourceType
from app.infrastructure.persistence.memory.clock import FixedClock
from tests.contracts.backends import ContractBackend
from tests.contracts.catalog_data import NOW
from tests.contracts.helpers import run_in_uow
from tests.contracts.purchasing_data import WHO, payment, purchase, same, supplier
from tests.contracts.stock_data import seed, units


def test_purchase_round_trip_with_children(backend: ContractBackend, shop_a: ShopId) -> None:
    bought = purchase(shop_a, 1)
    run_in_uow(backend, shop_a, lambda uow: PurchaseRepository.within(uow).add(bought))
    with backend.uow(shop_a) as uow:
        stored = PurchaseRepository.within(uow).get(bought.id)
        assert same(stored, bought)
        add_payment(stored, payment(300_000), performer=WHO)
        stored.cancel("doublon", performer=WHO, now=NOW)
        PurchaseRepository.within(uow).update(stored)
        uow.commit()
    with backend.uow(shop_a) as uow:
        again = PurchaseRepository.within(uow).get(bought.id)
    assert same(again, stored)
    assert again.version == 2
    assert str(again.costed[1].stock_quantity) == "9.1"


def test_numbers_suppliers_unique_and_isolated(
    backend: ContractBackend, shop_a: ShopId, shop_b: ShopId
) -> None:
    with backend.uow(shop_a) as uow:
        numbers = [str(uow.numbering.next(DocType.PURCHASE)) for _ in range(2)]
        uow.commit()
    assert numbers == ["A-000001", "A-000002"]  # PUR-05
    first = supplier(shop_a)
    run_in_uow(backend, shop_a, lambda uow: SupplierRepository.within(uow).add(first))
    clash = supplier(shop_a, " HAOJUE douala ")
    with pytest.raises(Duplicate) as refused:
        run_in_uow(backend, shop_a, lambda uow: SupplierRepository.within(uow).add(clash))
    assert refused.value.details["constraint"] == "supplier_name"
    run_in_uow(backend, shop_b, lambda uow: SupplierRepository.within(uow).add(supplier(shop_b)))
    bought = purchase(shop_a, 1)
    run_in_uow(backend, shop_a, lambda uow: PurchaseRepository.within(uow).add(bought))
    twin = purchase(shop_a, 1)
    with pytest.raises(Duplicate):
        run_in_uow(backend, shop_a, lambda uow: PurchaseRepository.within(uow).add(twin))
    with backend.uow(shop_b) as uow:
        with pytest.raises(NotFound):
            PurchaseRepository.within(uow).get(bought.id)  # SEC-I : autre boutique
        assert [s.name for s in SupplierRepository.within(uow).list_all()] == ["Haojue Douala"]


def test_optimistic_lock_and_period_listing(backend: ContractBackend, shop_a: ShopId) -> None:
    older = purchase(shop_a, 1, on=date(2026, 11, 3))
    newer = purchase(shop_a, 2, on=date(2026, 11, 9))
    outside = purchase(shop_a, 3, on=date(2026, 10, 30))

    def add_all(uow: UnitOfWork) -> None:
        for item in (older, newer, outside):
            PurchaseRepository.within(uow).add(item)

    run_in_uow(backend, shop_a, add_all)
    with backend.uow(shop_a) as uow:
        found = PurchaseRepository.within(uow).list_between(date(2026, 11, 1), date(2026, 11, 30))
    assert [str(p.number) for p in found] == ["A-000002", "A-000001"]
    stale = found[1]
    with backend.uow(shop_a) as uow:
        fresh = PurchaseRepository.within(uow).get(older.id)
        fresh.cancel("x", performer=WHO, now=NOW)
        PurchaseRepository.within(uow).update(fresh)
        uow.commit()
    stale.cancel("y", performer=WHO, now=NOW)
    update = partial(lambda uow: PurchaseRepository.within(uow).update(stale))
    with pytest.raises(VersionConflict):
        run_in_uow(backend, shop_a, update)


def test_costing_replay_on_ledger_gives_515000(backend: ContractBackend, shop_a: ShopId) -> None:
    data = seed(backend, shop_a)
    ledger = StockLedger(FixedClock(NOW))

    def post(kind: MovementType, quantity: int, day: int, cost: int | None = None) -> None:
        posting = Posting(
            article_id=data.article.id,
            location_id=data.garoua.id,
            type=kind,
            quantity=units(quantity),
            source=SourceRef(SourceType.PURCHASE, uuid4()),
            occurred_at=NOW + timedelta(days=day),
            author_id=WHO.user_id,
            unit_cost=None if cost is None else Money(cost),
        )
        with backend.uow(shop_a) as uow:
            post_ = ledger.record_exit if cost is None else ledger.record_entry
            movement = post_(uow, posting)
            refresh_costs(uow, [data.article.id])
            uow.commit()
        moves.append(movement)

    moves: list = []  # type: ignore[type-arg]
    post(MovementType.PURCHASE_IN, 10, 0, 500_000)
    post(MovementType.SALE_OUT, 5, 0)
    post(MovementType.PURCHASE_IN, 5, 1, 350_000)
    with backend.uow(shop_a) as uow:
        assert ArticleRepository.within(uow).get(data.article.id).wac == Money(425_000)
        assert str(quantity_left(uow, moves[0])) == "5"
        assert str(quantity_left(uow, moves[2])) == "0"
        ledger.reverse(uow, moves[2].id, source=moves[2].source, author_id=WHO.user_id,
                       occurred_at=NOW)  # fmt: skip
        uow.commit()
    post(MovementType.PURCHASE_IN, 5, 1, 530_000)  # la correction de P2, même date
    with backend.uow(shop_a) as uow:
        article = ArticleRepository.within(uow).get(data.article.id)
        state = replay_article(uow, data.article.id)
    assert (article.wac, article.last_cost) == (Money(515_000), Money(530_000))
    assert state.quantity == 10
