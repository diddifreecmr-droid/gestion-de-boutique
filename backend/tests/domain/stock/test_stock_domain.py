"""Domaine du stock : signes et coûts des mouvements, projection, ajustement, inventaire, valeur."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.audit.values import Performer
from app.domain.catalog.ids import ArticleId
from app.domain.shared.doc_number import DocNumber, DocType
from app.domain.shared.errors import InvalidQuantity, InvalidStateTransition, ValidationFailed
from app.domain.shared.ids import ShopId, UserId
from app.domain.shared.money import Money
from app.domain.shared.quantity import Quantity, StockUnit
from app.domain.shops.ids import LocationId
from app.domain.stock.adjustment import (
    Adjustment,
    AdjustmentDirection,
    AdjustmentDraft,
    AdjustmentReason,
)
from app.domain.stock.errors import ReasonRequired
from app.domain.stock.events import AdjustmentRecorded
from app.domain.stock.ids import InventoryId, StockMovementId
from app.domain.stock.inventory import Inventory, InventoryStatus
from app.domain.stock.inventory_line import InventoryLine, LineCheck
from app.domain.stock.level import StockLevel
from app.domain.stock.movement import StockMovement
from app.domain.stock.valuation import total_or_none, value_of
from app.domain.stock.values import (
    COSTED_ENTRIES,
    MovementType,
    SourceRef,
    SourceType,
    StockCondition,
)

NOW = datetime(2026, 11, 11, 9, 0, tzinfo=UTC)
SHOP, USER = ShopId.new(), UserId.new()
PERFORMER = Performer(USER, "accountant")


def qty(value: str, unit: StockUnit = StockUnit.UNIT) -> Quantity:
    return Quantity.of(value, unit)


def movement(
    kind: MovementType, value: str, cost: int | None = None, **extra: object
) -> StockMovement:
    return StockMovement(
        id=StockMovementId.new(),
        shop_id=SHOP,
        article_id=ArticleId.new(),
        location_id=LocationId.new(),
        type=kind,
        condition=StockCondition.SELLABLE,
        quantity=qty(value),
        balance_after=qty("0"),
        source=SourceRef(SourceType.IMPORT, uuid4()),
        occurred_at=NOW,
        recorded_at=NOW,
        author_id=USER,
        unit_cost=None if cost is None else Money(cost),
        **extra,  # type: ignore[arg-type]
    )


def test_movement_sign_and_cost_rules() -> None:
    assert movement(MovementType.OPENING, "3", 500_000).quantity.value == 3
    assert MovementType.ADJUSTMENT_OUT.label == "Ajustement -"
    assert {MovementType.PURCHASE_IN, MovementType.OPENING} == COSTED_ENTRIES
    for kind, value in ((MovementType.SALE_OUT, "1"), (MovementType.CUSTOMER_RETURN, "-1")):
        with pytest.raises(InvalidQuantity):
            movement(kind, value)
    with pytest.raises(InvalidQuantity):
        movement(MovementType.RESTORE, "0")
    with pytest.raises(ValidationFailed):
        movement(MovementType.PURCHASE_IN, "1")  # coût obligatoire
    with pytest.raises(ValidationFailed):
        movement(MovementType.SALE_OUT, "-1", 10)  # une sortie ne porte pas de coût
    with pytest.raises(ValueError, match="Annulation"):
        movement(MovementType.REVERSAL, "-1")
    reversal = movement(MovementType.REVERSAL, "-1", reverses=StockMovementId.new())
    assert reversal.reverses is not None
    with pytest.raises(TypeError):
        SourceRef(SourceType.SALE, "pas un uuid")  # type: ignore[arg-type]


def test_level_balances() -> None:
    level = StockLevel.empty(SHOP, ArticleId.new(), LocationId.new(), StockUnit.METER)
    assert not level.has_stock
    assert str(level.apply(qty("2.5", StockUnit.METER), StockCondition.SELLABLE)) == "2.5"
    assert str(level.apply(qty("1", StockUnit.METER), StockCondition.DAMAGED)) == "1.0"
    assert level.has_stock
    with pytest.raises(ValueError, match="unités"):
        StockLevel(
            id=level.id,
            shop_id=SHOP,
            article_id=level.article_id,
            location_id=level.location_id,
            sellable=qty("1"),
            damaged=qty("1", StockUnit.METER),
            incoming=qty("0"),
        )


def draft(**changes: object) -> AdjustmentDraft:
    values: dict[str, object] = {
        "location_id": LocationId.new(),
        "article_id": ArticleId.new(),
        "direction": AdjustmentDirection.OUT,
        "quantity": qty("1"),
        "condition": StockCondition.SELLABLE,
        "reason": AdjustmentReason.BREAKAGE,
    }
    return AdjustmentDraft(**(values | changes))  # type: ignore[arg-type]


def test_adjustment_rules() -> None:
    made = Adjustment.record(draft(), shop_id=SHOP, performer=PERFORMER, now=NOW, article_name="HJ")
    assert (made.movement_type, str(made.signed_quantity)) == (MovementType.ADJUSTMENT_OUT, "-1")
    event = made.events.pull()[0]
    assert isinstance(event, AdjustmentRecorded)
    assert event.audit_record().sensitive
    plus = Adjustment.record(
        draft(direction=AdjustmentDirection.IN),
        shop_id=SHOP,
        performer=PERFORMER,
        now=NOW,
        article_name="HJ",
    )
    assert plus.movement_type is MovementType.ADJUSTMENT_IN
    for bad in (
        draft(reason=AdjustmentReason.OTHER),
        draft(reason=AdjustmentReason.INVENTORY_GAP, note="x"),
        draft(quantity=qty("0")),
    ):
        with pytest.raises(ValidationFailed):
            Adjustment.record(bad, shop_id=SHOP, performer=PERFORMER, now=NOW, article_name="HJ")


def assert_closed(inventory: Inventory) -> None:
    assert (inventory.status, inventory.open_location_key) == (InventoryStatus.VALIDATED, None)


def test_inventory_lifecycle_and_masking() -> None:
    hj, dk = ArticleId.new(), ArticleId.new()
    inventory = Inventory.start(
        shop_id=SHOP,
        number=DocNumber(DocType.INVENTORY, 1),
        location_id=LocationId.new(),
        articles=[(hj, StockUnit.UNIT), (dk, StockUnit.UNIT)],
        performer=PERFORMER,
        now=NOW,
    )
    assert inventory.open_location_key == inventory.location_id
    inventory.record_counts({hj: qty("7"), dk: qty("2")}, performer=PERFORMER, now=NOW)
    assert all(
        line.theoretical is None and line.difference is None for line in inventory.lines.values()
    )
    with pytest.raises(ValidationFailed):
        inventory.record_counts({ArticleId.new(): qty("1")}, performer=PERFORMER, now=NOW)
    checks = {hj: LineCheck(qty("8"), Money(540_000)), dk: LineCheck(qty("2"), None)}
    with pytest.raises(ReasonRequired):
        inventory.validate(checks, reasons={}, global_reason=None, performer=PERFORMER, now=NOW)
    gaps = inventory.validate(
        checks, reasons={hj: "Vol"}, global_reason=None, performer=PERFORMER, now=NOW
    )
    assert [(line.article_id, str(line.difference)) for line in gaps] == [(hj, "-1")]
    assert inventory.gap_value == Money(-540_000)
    assert_closed(inventory)
    with pytest.raises(InvalidStateTransition):
        inventory.abandon(performer=PERFORMER, now=NOW)
    with pytest.raises(ValueError, match="unité"):
        InventoryLine(article_id=hj, unit=StockUnit.METER, counted=qty("1"))
    with pytest.raises(InvalidQuantity):
        InventoryLine(article_id=hj, unit=StockUnit.UNIT, counted=qty("-1"))
    assert InventoryId.new() != inventory.id


def test_valuation_rounding_and_unknown() -> None:
    assert value_of(qty("2.5", StockUnit.METER), Money(1_001)) == Money(2_503)  # 2502,5 → 2503
    assert value_of(qty("1"), None) is None
    assert total_or_none([Money(1), Money(2)]) == Money(3)
    assert total_or_none([Money(1), None]) is None
