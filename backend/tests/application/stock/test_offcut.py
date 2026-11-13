"""UC-TEX-03 — déclarer une chute (RG-X06, TEX-05) : sortie « Chute » au dixième de mètre,
avec note et photo ; sens « + » refusé ; journal sensible ; l'inventaire suivant ne la compte
pas comme un manquant (elle a déjà baissé le théorique)."""

import pytest

from app.application.audit.ports import AuditQuery
from app.application.security.errors import PermissionDenied
from app.application.stock.use_cases.record_adjustment import AdjustmentCommand
from app.domain.catalog.ids import AttachmentId
from app.domain.shared.errors import InvalidQuantity, ValidationFailed
from app.domain.stock.adjustment import AdjustmentDirection, AdjustmentReason
from app.domain.stock.values import MovementType, StockCondition
from tests.application.sales.textile_support import STORE, TextileWorld

OFFCUT = AdjustmentReason.OFFCUT


def test_offcut_of_0_4_m_with_note_and_photo() -> None:
    world = TextileWorld()
    wax = world.wax()
    world.stock_in(world.x_owner, wax, STORE, "10", cost=2_004)
    photo = AttachmentId.new()
    command = AdjustmentCommand(
        location_id=world.loc(world.x_owner, STORE),
        article_id=wax.id,
        direction=AdjustmentDirection.OUT,
        quantity="0.4",
        condition=StockCondition.SELLABLE,
        reason=OFFCUT,
        note="bout taché",
        photo_id=photo,
    )
    done = world.stock_http.adjust.execute(world.accountant, command)
    assert (done.adjustment.photo_id, done.adjustment.note) == (photo, "bout taché")
    assert done.movement is not None
    assert (done.movement.type, done.movement.type.label) == (MovementType.OFFCUT, "Chute")
    assert (str(done.movement.quantity), str(done.movement.balance_after)) == ("-0.4", "9.6")
    assert world.matrix_total(world.x_owner, wax) == "9.6"
    assert world.x_owner.shop_id is not None
    entries = world.journal(world.x_owner.shop_id, AuditQuery(entity_type="adjustment"))
    [entry] = entries
    assert (entry.summary, entry.sensitive) == ("Chute -0.4 : Wax Fleur de mariage", True)


def test_offcut_rules_and_rights() -> None:
    world = TextileWorld()
    wax = world.wax()
    world.stock_in(world.x_owner, wax, STORE, "10")
    with pytest.raises(ValidationFailed) as inward:
        world.adjust(world.x_owner, wax, STORE, "0.4", AdjustmentDirection.IN, OFFCUT)
    assert inward.value.details["field"] == "direction"
    with pytest.raises(InvalidQuantity):
        world.adjust(world.x_owner, wax, STORE, "0.45", reason=OFFCUT)  # au dixième
    with pytest.raises(PermissionDenied):  # M3-08 : l'employé ne déclare pas de chute
        world.adjust(world.employee, wax, STORE, "0.4", reason=OFFCUT)
    assert world.matrix_total(world.x_owner, wax) == "10.0"


def test_offcut_is_not_an_inventory_gap() -> None:
    world = TextileWorld()
    wax = world.wax()
    world.stock_in(world.x_owner, wax, STORE, "10")
    world.adjust(world.x_owner, wax, STORE, "0.4", reason=OFFCUT)
    inventories = world.stock_http
    sheet, _ = inventories.start_inventory.execute(
        world.accountant, world.loc(world.x_owner, STORE)
    )
    inventory = sheet.inventory
    inventories.counts.execute(world.accountant, inventory.id, {wax.id: "9.6"}, 1)
    done = inventories.validate_inventory.execute(world.accountant, inventory.id, 2)
    line = done.inventory.lines[wax.id]
    assert (str(line.theoretical), str(line.difference)) == ("9.6", "0.0")
    kinds = [move.type for move in world.movements(world.x_owner, wax)]
    assert MovementType.OFFCUT in kinds  # la chute reste visible dans l'historique
