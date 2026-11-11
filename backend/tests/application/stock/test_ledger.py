"""Grand livre (TR-12, TR-13, RG-T16 à RG-T18 ; ERR-STK-01, OFF-06) par la composition root."""

from uuid import uuid4

import pytest

from app.application.stock.ports import StockLevelRepository, StockMovementLog
from app.application.stock.postings import Posting
from app.application.stock.retry import with_stock_retry
from app.domain.alerts.alert import AlertType
from app.domain.shared.errors import (
    Duplicate,
    InvalidQuantity,
    InvalidStateTransition,
    NotFound,
    ValidationFailed,
    VersionConflict,
)
from app.domain.shared.quantity import Quantity, StockUnit
from app.domain.stock.errors import MovementAlreadyReversed, StockInsufficient
from app.domain.stock.ids import StockMovementId
from app.domain.stock.movement import StockMovement
from app.domain.stock.values import MovementType, SourceRef, SourceType
from tests.application.stock.support import StockWorld


def test_entries_exits_and_insufficient_stock_details() -> None:
    world = StockWorld()
    owner, _, _, hj = world.setup()
    world.stock_in(owner, hj, "Garoua", 2)
    world.stock_in(owner, hj, "Garoua-Boulaï", 5)
    with pytest.raises(StockInsufficient) as refused:
        world.sell(owner, hj, "Garoua", 3)  # ERR-STK-01
    details = refused.value.details
    assert (details["available"], details["requested"]) == ("2", "3")
    others = details["other_locations"]
    assert isinstance(others, list)
    assert [(o["location_name"], o["available"]) for o in others] == [("Garoua-Boulaï", "5")]
    sold = world.sell(owner, hj, "Garoua", 2)  # ERR-STK-03
    assert (str(sold.quantity), str(sold.balance_after), sold.stock_to_verify) == ("-2", "0", False)
    assert world.matrix_total(owner, hj) == "5"
    types = [m.type for m in world.movements(owner, hj)]
    assert types == [MovementType.SALE_OUT, MovementType.OPENING, MovementType.OPENING]


def test_projection_equals_sum_of_movements() -> None:
    world = StockWorld()
    owner, _, _, hj = world.setup()
    for quantity in (3, 4, 1):
        world.stock_in(owner, hj, "Garoua", quantity)
    for quantity in (2, 5):
        world.sell(owner, hj, "Garoua", quantity)
    total = sum(m.quantity.value for m in world.movements(owner, hj))
    with world.core.shop_uow_factory(world.shop_of(owner)) as uow:
        level = StockLevelRepository.within(uow).find_level(hj.id, world.loc(owner, "Garoua"))
    assert level is not None
    assert level.sellable.value == total == 1  # RG-T16
    assert level.version == 5


def test_deferred_exit_marks_stock_to_verify_and_alerts() -> None:
    world = StockWorld()
    owner, accountant, seller, hj = world.setup()
    world.stock_in(owner, hj, "Garoua", 1)
    late = world.sell(seller, hj, "Garoua", 2, deferred=True)  # OFF-06
    assert (str(late.balance_after), late.stock_to_verify) == ("-1", True)
    for who in (owner, accountant):
        kinds = [alert.type for alert in world.alerts(owner, who)]
        assert AlertType.STOCK_TO_VERIFY in kinds
    assert world.alerts(owner, seller) == []


def test_reverse_once_and_reversal_rules() -> None:
    world = StockWorld()
    owner, _, _, hj = world.setup()
    entry = world.stock_in(owner, hj, "Garoua", 3)
    sale = world.sell(owner, hj, "Garoua", 1)
    source = SourceRef(SourceType.SALE, sale.source.id)

    def reverse(movement_id: StockMovementId) -> StockMovement:
        with world.core.shop_uow_factory(world.shop_of(owner)) as uow:
            done = world.ledger.reverse(
                uow,
                movement_id,
                source=source,
                author_id=owner.user_id,
                occurred_at=world.clock.now(),
            )
            uow.commit()
        return done

    reversal = reverse(sale.id)
    assert str(reversal.balance_after) == "3"
    with pytest.raises(MovementAlreadyReversed):
        reverse(sale.id)
    with pytest.raises(InvalidStateTransition):
        reverse(reversal.id)
    with pytest.raises(NotFound):
        reverse(StockMovementId.new())
    world.sell(owner, hj, "Garoua", 3)
    with pytest.raises(StockInsufficient):
        reverse(entry.id)  # une entrée déjà vendue ne s'annule pas (RG-T17)
    with world.core.shop_uow_factory(world.shop_of(owner)) as uow:
        log = StockMovementLog.within(uow)
        assert [m.id for m in log.for_source(sale.source.id)] == [sale.id, reversal.id]


def test_preconditions_fail_fast() -> None:
    world = StockWorld()
    owner, _, _, hj = world.setup()
    garoua = world.loc(owner, "Garoua")

    def posting(kind: MovementType, unit: StockUnit = StockUnit.UNIT, amount: int = 1) -> Posting:
        return Posting(
            article_id=hj.id,
            location_id=garoua,
            type=kind,
            quantity=Quantity.of(amount, unit),
            source=SourceRef(SourceType.IMPORT, uuid4()),
            occurred_at=world.clock.now(),
            author_id=owner.user_id,
        )

    with world.core.shop_uow_factory(world.shop_of(owner)) as uow:
        with pytest.raises(ValueError, match="type d'entrée"):
            world.ledger.record_entry(uow, posting(MovementType.SALE_OUT))
        with pytest.raises(ValueError, match="type de sortie"):
            world.ledger.record_exit(uow, posting(MovementType.OPENING))
        with pytest.raises(ValidationFailed):  # Reprise de départ sans coût
            world.ledger.record_entry(uow, posting(MovementType.OPENING))
        with pytest.raises(ValueError, match="unité"):
            world.ledger.record_entry(uow, posting(MovementType.CUSTOMER_RETURN, StockUnit.METER))
        uow.rollback()
    with pytest.raises(InvalidQuantity):
        posting(MovementType.CUSTOMER_RETURN, amount=0)
    depot = world.location(world.shop_of(owner), "Ngaoundéré")
    world.http.locations.update(owner, depot.id, {"active": False}, depot.version)
    with pytest.raises(ValidationFailed):
        world.stock_in(owner, hj, "Ngaoundéré", 1)


def test_retry_replays_only_stock_races() -> None:
    calls: list[int] = []

    def flaky() -> str:
        calls.append(1)
        if len(calls) < 3:
            raise VersionConflict("conflit")
        return "ok"

    assert with_stock_retry(flaky) == "ok"
    assert len(calls) == 3
    always = VersionConflict("toujours")
    with pytest.raises(VersionConflict):
        with_stock_retry(lambda: (_ for _ in ()).throw(always))
    other = Duplicate("x", details={"constraint": "autre"})
    with pytest.raises(Duplicate):
        with_stock_retry(lambda: (_ for _ in ()).throw(other))
    level_race = Duplicate("x", details={"constraint": "stock_level_article_location"})
    with pytest.raises(Duplicate):
        with_stock_retry(lambda: (_ for _ in ()).throw(level_race), attempts=2)
    with pytest.raises(ValueError, match="tentative"):
        with_stock_retry(lambda: 1, attempts=0)
