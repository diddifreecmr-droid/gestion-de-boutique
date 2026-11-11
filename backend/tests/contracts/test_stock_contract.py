"""Contrat des ports du stock (T14) : projection, grand livre, ajustements, inventaires, et le
grand livre de bout en bout (RG-T16 : projection = somme des mouvements, RG-T17)."""

from datetime import timedelta
from uuid import uuid4

import pytest

from app.application.ports.errors import IsolationViolation
from app.application.ports.pagination import PageRequest
from app.application.stock.ports import (
    INVENTORY_OPEN_LOCATION,
    STOCK_LEVEL_KEY,
    AdjustmentRepository,
    InventoryRepository,
    StockLevelRepository,
    StockMovementLog,
)
from app.domain.audit.values import Performer
from app.domain.shared.doc_number import DocNumber, DocType
from app.domain.shared.errors import Duplicate, VersionConflict
from app.domain.shared.ids import ShopId
from app.domain.shared.quantity import StockUnit
from app.domain.stock.adjustment import (
    Adjustment,
    AdjustmentDirection,
    AdjustmentDraft,
    AdjustmentReason,
)
from app.domain.stock.inventory import Inventory
from app.domain.stock.inventory_line import LineCheck
from app.domain.stock.level import StockLevel
from app.domain.stock.values import MovementType, StockCondition
from tests.contracts.backends import ContractBackend
from tests.contracts.catalog_data import NOW
from tests.contracts.helpers import run_in_uow
from tests.contracts.stock_data import AUTHOR, movement, seed, units

PERFORMER = Performer(AUTHOR, "accountant")


def test_level_round_trip_unique_lock_and_isolation(
    backend: ContractBackend, shop_a: ShopId, shop_b: ShopId
) -> None:
    data = seed(backend, shop_a)
    level = StockLevel.empty(shop_a, data.article.id, data.garoua.id, StockUnit.UNIT)
    level.apply(units(3), StockCondition.SELLABLE)
    run_in_uow(backend, shop_a, lambda uow: StockLevelRepository.within(uow).add(level))
    twin = StockLevel.empty(shop_a, data.article.id, data.garoua.id, StockUnit.UNIT)
    with pytest.raises(Duplicate) as clash:
        run_in_uow(backend, shop_a, lambda uow: StockLevelRepository.within(uow).add(twin))
    assert clash.value.details["constraint"] == STOCK_LEVEL_KEY
    with backend.uow(shop_a) as uow:
        levels = StockLevelRepository.within(uow)
        found = levels.find_level(data.article.id, data.garoua.id)
        assert found is not None
        assert (str(found.sellable), found.version) == ("3", 1)
        assert levels.find_level(data.article.id, data.depot.id) is None
        assert [lv.id for lv in levels.for_article(data.article.id)] == [level.id]
        assert [lv.id for lv in levels.for_location(data.garoua.id)] == [level.id]
        assert levels.for_location(data.depot.id) == []
        assert len(levels.list_all()) == 1
    with backend.uow(shop_a) as uow:
        stale = StockLevelRepository.within(uow).get(level.id)
    with backend.uow(shop_a) as uow:
        fresh = StockLevelRepository.within(uow).get(level.id)
    fresh.apply(units(-1), StockCondition.SELLABLE)
    run_in_uow(backend, shop_a, lambda uow: StockLevelRepository.within(uow).update(fresh))
    stale.apply(units(-1), StockCondition.SELLABLE)
    with pytest.raises(VersionConflict):
        run_in_uow(backend, shop_a, lambda uow: StockLevelRepository.within(uow).update(stale))
    with backend.uow(shop_b) as uow:
        assert StockLevelRepository.within(uow).list_all() == []
        with pytest.raises(IsolationViolation):
            StockLevelRepository.within(uow).add(twin)


def test_movement_log_append_only_order_and_counts(
    backend: ContractBackend, shop_a: ShopId, shop_b: ShopId
) -> None:
    data = seed(backend, shop_a)
    aid, garoua = data.article.id, data.garoua.id
    sale = uuid4()
    first = movement(shop_a, aid, garoua, quantity=5)
    late = movement(shop_a, aid, garoua, kind=MovementType.SALE_OUT, minutes=20, source=sale)
    same = movement(shop_a, aid, garoua, kind=MovementType.SALE_OUT, minutes=20, source=sale)
    early = movement(shop_a, aid, data.depot.id, quantity=2, minutes=-30)
    undo = movement(
        shop_a, aid, garoua, kind=MovementType.REVERSAL, quantity=1, minutes=30, reverses=late.id
    )
    written = [first, late, same, early, undo]
    with backend.uow(shop_a) as uow:
        for item in written:
            StockMovementLog.within(uow).append(item)
        uow.commit()
    with backend.uow(shop_a) as uow:
        log = StockMovementLog.within(uow)
        assert log.find(first.id) == first
        assert log.reversal_of(late.id) == undo
        assert log.reversal_of(first.id) is None
        assert [m.id for m in log.for_source(sale)] == sorted([late.id, same.id])
        page = log.for_article(aid, PageRequest(limit=2))
        assert page.items == [undo, max(late, same, key=lambda m: m.id)]
        assert page.next_cursor is not None
        rest = log.for_article(aid, PageRequest(10, page.next_cursor))
        assert [m.id for m in rest.items] == [
            min(late, same, key=lambda m: m.id).id,
            first.id,
            early.id,
        ]
        since = NOW + timedelta(minutes=10)
        assert log.count_sources_since(garoua, MovementType.SALE_OUT, since) == 1
        assert log.count_sources_since(garoua, MovementType.SALE_OUT, NOW + timedelta(hours=1)) == 0
    assert not hasattr(StockMovementLog, "update")
    with pytest.raises(Duplicate):
        run_in_uow(backend, shop_a, lambda uow: StockMovementLog.within(uow).append(first))
    with backend.uow(shop_b) as uow:
        assert StockMovementLog.within(uow).find(first.id) is None
        with pytest.raises(IsolationViolation):
            StockMovementLog.within(uow).append(first)


def test_adjustment_and_inventory_round_trip(backend: ContractBackend, shop_a: ShopId) -> None:
    data = seed(backend, shop_a)
    aid, garoua = data.article.id, data.garoua.id
    draft = AdjustmentDraft(
        location_id=garoua,
        article_id=aid,
        direction=AdjustmentDirection.OUT,
        quantity=units(1),
        condition=StockCondition.DAMAGED,
        reason=AdjustmentReason.OTHER,
        note="Rayure",
    )
    adjustment = Adjustment.record(
        draft, shop_id=shop_a, performer=PERFORMER, now=NOW, article_name="HJ"
    )
    adjustment.events.pull()
    inventory = Inventory.start(
        shop_id=shop_a,
        number=DocNumber(DocType.INVENTORY, 1),
        location_id=garoua,
        articles=[(aid, StockUnit.UNIT)],
        performer=PERFORMER,
        now=NOW,
    )
    inventory.events.pull()
    with backend.uow(shop_a) as uow:
        AdjustmentRepository.within(uow).add(adjustment)
        InventoryRepository.within(uow).add(inventory)
        uow.commit()
    second = Inventory.start(
        shop_id=shop_a,
        number=DocNumber(DocType.INVENTORY, 2),
        location_id=garoua,
        articles=[],
        performer=PERFORMER,
        now=NOW,
    )
    second.events.pull()
    with pytest.raises(Duplicate) as clash:
        run_in_uow(backend, shop_a, lambda uow: InventoryRepository.within(uow).add(second))
    assert clash.value.details["constraint"] == INVENTORY_OPEN_LOCATION
    with backend.uow(shop_a) as uow:
        read = AdjustmentRepository.within(uow).get(adjustment.id)
        assert (read.note, read.quantity, read.condition) == (
            "Rayure",
            units(1),
            StockCondition.DAMAGED,
        )
        inventories = InventoryRepository.within(uow)
        stored = inventories.find_open(garoua)
        assert stored is not None
        assert str(stored.number) == "INV-000001"
        stored.record_counts({aid: units(4)}, performer=PERFORMER, now=NOW)
        stored.validate(
            {aid: LineCheck(units(3), None)},
            reasons={aid: "Recompte"},
            global_reason=None,
            performer=PERFORMER,
            now=NOW,
        )
        inventories.update(stored)
        uow.commit()
    with backend.uow(shop_a) as uow:
        inventories = InventoryRepository.within(uow)
        assert inventories.find_open(garoua) is None
        line = inventories.get(inventory.id).lines[aid]
        assert (str(line.counted), str(line.theoretical), line.reason, line.gap_value) == (
            "4",
            "3",
            "Recompte",
            None,
        )
    run_in_uow(backend, shop_a, lambda uow: InventoryRepository.within(uow).add(second))
