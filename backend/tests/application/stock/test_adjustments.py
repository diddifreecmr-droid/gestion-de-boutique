"""UC-STK-08 — ajustements (ADJ-01 à ADJ-05) ; journal sensible, alerte au propriétaire."""

import pytest

from app.application.audit.ports import AuditLog, AuditQuery
from app.application.ports.pagination import PageRequest
from app.application.security.errors import PermissionDenied
from app.domain.alerts.alert import AlertType
from app.domain.shared.errors import InvalidQuantity, ValidationFailed
from app.domain.stock.adjustment import AdjustmentDirection, AdjustmentReason
from app.domain.stock.errors import StockInsufficient
from app.domain.stock.ids import AdjustmentId
from app.domain.stock.values import MovementType, SourceType, StockCondition
from tests.application.stock.support import StockWorld


def test_adjustment_out_in_and_offcut() -> None:
    world = StockWorld()
    owner, accountant, _, hj = world.setup()
    world.stock_in(owner, hj, "Garoua", 2)
    world.set_costs(owner, hj, 540_000, 530_000)
    out = world.adjust(accountant, hj, "Garoua", "1")  # ADJ-01
    assert out.movement is not None
    assert (out.movement.type, str(out.movement.balance_after)) == (
        MovementType.ADJUSTMENT_OUT,
        "1",
    )
    assert out.movement.source.type is SourceType.ADJUSTMENT
    assert out.movement.unit_cost is None
    entry = world.adjust(
        owner, hj, "Garoua", "2", AdjustmentDirection.IN, AdjustmentReason.ENTRY_ERROR
    )
    assert entry.movement is not None
    assert entry.movement.unit_cost is not None
    assert entry.movement.unit_cost.amount == 530_000  # Q-16 : CMP courant, CMP inchangé
    offcut = world.adjust(owner, hj, "Garoua", "1", reason=AdjustmentReason.OFFCUT)
    assert offcut.movement is not None
    assert offcut.movement.type is MovementType.OFFCUT
    damaged = world.adjust(
        owner,
        hj,
        "Garoua",
        "1",
        AdjustmentDirection.IN,
        AdjustmentReason.OTHER,
        condition=StockCondition.DAMAGED,
        note="Rayure",
    )
    assert damaged.movement is not None
    assert str(damaged.movement.balance_after) == "1"
    assert world.matrix_total(owner, hj) == "2"
    assert world.article(owner, hj).wac is not None


def test_adjustment_rules_and_rights() -> None:
    world = StockWorld()
    owner, _, seller, hj = world.setup()
    world.stock_in(owner, hj, "Garoua", 2)
    with pytest.raises(StockInsufficient) as refused:  # ADJ-04 / ERR-STK-04
        world.adjust(owner, hj, "Garoua", "3")
    assert refused.value.details["available"] == "2"
    with pytest.raises(ValidationFailed):  # ADJ-02 : « Autre » sans note
        world.adjust(owner, hj, "Garoua", "1", reason=AdjustmentReason.OTHER)
    with pytest.raises(InvalidQuantity):
        world.adjust(owner, hj, "Garoua", "0")
    with pytest.raises(InvalidQuantity):
        world.adjust(owner, hj, "Garoua", "1.5")  # RG-T08
    with pytest.raises(ValidationFailed):
        world.adjust(owner, hj, "Garoua", "1", reason=AdjustmentReason.INVENTORY_GAP)
    with pytest.raises(PermissionDenied):
        world.adjust(seller, hj, "Garoua", "1")


def test_idempotent_replay_and_alert_for_accountant_only() -> None:
    world = StockWorld()
    owner, accountant, _, hj = world.setup()
    world.stock_in(owner, hj, "Garoua", 5)
    wanted = AdjustmentId.new()
    first = world.adjust(accountant, hj, "Garoua", "1", adjustment_id=wanted)
    replay = world.adjust(accountant, hj, "Garoua", "1", adjustment_id=wanted)
    assert (replay.adjustment.id, replay.movement) == (wanted, None)
    assert first.movement is not None
    assert world.matrix_total(owner, hj) == "4"
    adjustments = [a for a in world.alerts(owner, owner) if a.type is AlertType.STOCK_ADJUSTMENT]
    assert len(adjustments) == 1  # ADJ-03 : par C → alerte à O
    world.adjust(owner, hj, "Garoua", "1")
    adjustments = [a for a in world.alerts(owner, owner) if a.type is AlertType.STOCK_ADJUSTMENT]
    assert len(adjustments) == 1  # par O → aucune alerte
    assert world.alerts(owner, accountant) == []
    with world.core.shop_uow_factory(world.shop_of(owner)) as uow:
        entries = AuditLog.within(uow).search(AuditQuery(entity_type="adjustment"), PageRequest())
    sensitive = [e for e in entries.items if e.entity.type == "adjustment"]
    assert len(sensitive) == 2
    assert all(entry.sensitive for entry in sensitive)  # AUD-02
