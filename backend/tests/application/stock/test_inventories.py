"""UC-STK-07 — inventaires (INV-01 à INV-06) par la composition root."""

from decimal import Decimal

import pytest

from app.application.security.errors import PermissionDenied
from app.domain.alerts.alert import AlertType
from app.domain.shared.errors import InvalidStateTransition, ValidationFailed, VersionConflict
from app.domain.stock.errors import InventoryAlreadyOpen, ReasonRequired
from app.domain.stock.ids import InventoryId
from app.domain.stock.inventory import InventoryStatus
from app.domain.stock.values import MovementType, SourceType
from tests.application.stock.support import StockWorld


def test_start_mask_count_resume_and_validate() -> None:
    world = StockWorld()
    owner, accountant, _, hj = world.setup()
    dk = world.moto(owner, model="DK150")
    world.stock_in(owner, hj, "Garoua", 10)
    world.stock_in(owner, dk, "Garoua", 3)
    world.set_costs(owner, hj, 540_000, 540_000)
    inventories = world.stock_http
    sheet, created = inventories.start_inventory.execute(accountant, world.loc(owner, "Garoua"))
    inventory = sheet.inventory
    assert (created, str(inventory.number), inventory.status) == (
        True,
        "INV-000001",
        InventoryStatus.IN_PROGRESS,
    )
    assert all(line.theoretical is None for line in inventory.lines.values())  # INV-01
    world.sell(owner, hj, "Garoua", 1)
    world.sell(owner, hj, "Garoua", 1)
    counted = inventories.counts.execute(accountant, inventory.id, {hj.id: "7"}, 1)
    assert counted.sales_since_start == 2  # INV-06
    with pytest.raises(ValidationFailed):  # DK150 pas encore compté
        inventories.validate_inventory.execute(accountant, inventory.id, 2)
    resumed = inventories.counts.execute(accountant, inventory.id, {dk.id: Decimal(3)}, 2)  # INV-02
    assert resumed.inventory.lines[hj.id].counted is not None
    with pytest.raises(ReasonRequired) as missing:
        inventories.validate_inventory.execute(accountant, inventory.id, 3)
    assert missing.value.details["articles"] == [str(hj.id)]
    done = inventories.validate_inventory.execute(
        accountant, inventory.id, 3, reasons={hj.id: "Vol constaté"}
    )
    line = done.inventory.lines[hj.id]
    assert (str(line.theoretical), str(line.difference), line.reason) == ("8", "-1", "Vol constaté")
    assert line.gap_value is not None
    assert line.gap_value.amount == -540_000  # INV-03 : écart x CMP
    assert done.inventory.status is InventoryStatus.VALIDATED
    assert done.sales_since_start == 0
    assert world.matrix_total(owner, hj) == "7"
    gap = world.movements(owner, hj)[0]
    assert (gap.type, gap.source.type, gap.source.number) == (
        MovementType.ADJUSTMENT_OUT,
        SourceType.INVENTORY,
        "INV-000001",
    )
    alerts = [a for a in world.alerts(owner, owner) if a.type is AlertType.INVENTORY_VALIDATED]
    assert len(alerts) == 1  # INV-04
    assert "540 000" in alerts[0].message
    assert not [a for a in world.alerts(owner, owner) if a.type is AlertType.STOCK_ADJUSTMENT]


def test_one_open_inventory_per_location_and_abandon() -> None:
    world = StockWorld()
    owner, accountant, seller, hj = world.setup()
    world.stock_in(owner, hj, "Garoua", 1)
    garoua = world.loc(owner, "Garoua")
    flow = world.stock_http
    wanted = InventoryId.new()
    first, _ = flow.start_inventory.execute(accountant, garoua, wanted)
    replay, created = flow.start_inventory.execute(accountant, garoua, wanted)
    assert (created, replay.inventory.id) == (False, wanted)
    with pytest.raises(InventoryAlreadyOpen):  # INV-05
        flow.start_inventory.execute(owner, garoua)
    other, _ = flow.start_inventory.execute(owner, world.loc(owner, "Ngaoundéré"))
    assert str(other.inventory.number) == "INV-000002"
    with pytest.raises(VersionConflict):
        flow.abandon_inventory.execute(accountant, first.inventory.id, 7)
    abandoned = flow.abandon_inventory.execute(accountant, first.inventory.id, 1)
    assert abandoned.inventory.status is InventoryStatus.ABANDONED
    with pytest.raises(InvalidStateTransition):
        flow.counts.execute(accountant, first.inventory.id, {hj.id: "1"}, 2)
    again, _ = flow.start_inventory.execute(accountant, garoua)
    assert again.inventory.status is InventoryStatus.IN_PROGRESS
    with pytest.raises(PermissionDenied):
        flow.get_inventory.execute(seller, again.inventory.id)
    with pytest.raises(ValidationFailed):
        flow.counts.execute(accountant, again.inventory.id, {InventoryId.new(): "1"}, 1)  # type: ignore[dict-item]
    seen = flow.get_inventory.execute(owner, again.inventory.id)
    assert (seen.location_name, seen.article_names[hj.id]) == ("Garoua", "Haojue HJ125-8")


def test_global_reason_and_unknown_cost() -> None:
    world = StockWorld()
    owner, _, _, hj = world.setup()
    world.stock_in(owner, hj, "Garoua", 2)
    flow = world.stock_http
    sheet, _ = flow.start_inventory.execute(owner, world.loc(owner, "Garoua"))
    flow.counts.execute(owner, sheet.inventory.id, {hj.id: "4"}, 1)
    done = flow.validate_inventory.execute(owner, sheet.inventory.id, 2, global_reason="Recompte")
    line = done.inventory.lines[hj.id]
    assert (str(line.difference), line.reason, line.gap_value) == ("2", "Recompte", None)
    assert done.inventory.gap_value is None  # CMP inconnu : non calculable
    assert world.matrix_total(owner, hj) == "4"
    alert = next(a for a in world.alerts(owner, owner) if a.type is AlertType.INVENTORY_VALIDATED)
    assert "non calculable" in alert.message
