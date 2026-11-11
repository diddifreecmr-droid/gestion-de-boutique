"""UC-ACH-03/04 : SCN-04 (variantes 1, 2, 3 → 510 000, 510 000, 515 000), PUR-06 (quantité
sortie), PUR-07 (7 jours, horloge contrôlable), PUR-08 (motif), PUR-09, PUR-10 (annulation)."""

from datetime import date

import pytest

from app.application.audit.ports import AuditQuery
from app.application.purchasing.use_cases.correct_purchase import CorrectPurchaseCommand
from app.application.security.errors import PermissionDenied
from app.domain.purchasing.errors import (
    CorrectionWindowClosed,
    PriceGapToConfirm,
    ReasonRequired,
    StockAlreadyLeft,
)
from app.domain.purchasing.rules import PurchaseStatus
from app.domain.shared.errors import InvalidStateTransition, VersionConflict
from app.domain.stock.values import MovementType
from tests.application.purchasing.support import PurchasingWorld, costs


def day(n: int) -> date:
    return date(2026, 11, n)


def scn04(world: PurchasingWorld, *, sale_before_p2: int = 0):  # type: ignore[no-untyped-def]
    owner, accountant, _, hj = world.setup()
    world.at(day(1))
    world.buy(accountant, hj, 10, 500_000)
    if sale_before_p2:
        world.at(day(1), hour=15)
        world.sell(owner, hj, "Garoua", sale_before_p2)
    world.at(day(2))
    p2 = world.buy(accountant, hj, 5, 350_000, confirm=False)  # -30 % exact : pas de message
    return owner, accountant, hj, p2


def test_scn04_v1_correction_replays_wac_to_510000() -> None:
    world = PurchasingWorld()
    owner, accountant, hj, p2 = scn04(world)
    assert costs(world, owner, hj) == (350_000, 450_000)
    world.at(day(3))
    fixed = world.correct(accountant, p2, lines=world.line(hj, 5, 530_000))
    purchase = fixed.purchase
    assert (str(purchase.number), purchase.version) == ("A-000002", 2)
    assert costs(world, owner, hj) == (530_000, 510_000)
    assert world.matrix_total(owner, hj) == "15"
    entries = world.journal(world.shop_of(owner), AuditQuery(entity_type="purchase"))
    update = next(e for e in entries if e.reason == "faute de frappe")
    assert [(c.field, c.before, c.after) for c in update.changes] == [
        ("line_1_unit_price", 350_000, 530_000)
    ]
    assert update.sensitive


def test_scn04_v2_sale_after_p2_keeps_frozen_costs_elsewhere() -> None:
    world = PurchasingWorld()
    owner, accountant, hj, p2 = scn04(world)
    world.at(day(2), hour=15)
    world.sell(owner, hj, "Garoua", 1)
    world.at(day(3))
    world.correct(accountant, p2, lines=world.line(hj, 5, 530_000))
    assert costs(world, owner, hj) == (530_000, 510_000)
    assert world.matrix_total(owner, hj) == "14"


def test_scn04_v3_replay_on_real_stock_gives_515000() -> None:
    world = PurchasingWorld()
    owner, accountant, hj, p2 = scn04(world, sale_before_p2=5)
    assert costs(world, owner, hj) == (350_000, 425_000)
    world.at(day(3))
    world.correct(accountant, p2, lines=world.line(hj, 5, 530_000))
    assert costs(world, owner, hj) == (530_000, 515_000)  # décision client Q-02


def test_pur06_correction_refused_below_what_left() -> None:
    world = PurchasingWorld()
    owner, accountant, _, hj = world.setup()
    bought = world.buy(accountant, hj, 10, 500_000)
    world.sell(owner, hj, "Garoua", 8)
    with pytest.raises(StockAlreadyLeft) as refused:
        world.correct(accountant, bought, lines=world.line(hj, 7, 500_000))
    assert (refused.value.details["left"], refused.value.details["requested"]) == ("8", "7")
    world.correct(accountant, bought, lines=world.line(hj, 8, 500_000))
    assert world.matrix_total(owner, hj) == "0"
    types = [m.type for m in world.movements(owner, hj)]
    assert types.count(MovementType.REVERSAL) == 1
    assert types.count(MovementType.PURCHASE_IN) == 2


def test_pur07_accountant_window_and_pur08_reason() -> None:
    world = PurchasingWorld()
    owner, accountant, _, hj = world.setup()
    world.at(day(3))
    bought = world.buy(accountant, hj, 2, 500_000)
    world.at(day(10))
    with pytest.raises(ReasonRequired):
        world.correct(accountant, bought, reason=" ", note="x")
    world.correct(accountant, bought, note="facture reçue")  # J+7 : accepté
    world.at(day(11))
    with pytest.raises(CorrectionWindowClosed):
        world.correct(accountant, bought, note="trop tard")
    assert world.correct(owner, bought, note="propriétaire").purchase.version == 3
    stale = CorrectPurchaseCommand(
        purchase_id=bought.purchase.id, version=1, reason="x", patch={"note": "y"}
    )
    with pytest.raises(VersionConflict):
        world.purchasing.correct.execute(owner, stale)


def test_correction_compares_price_to_last_cost_without_this_purchase() -> None:
    world = PurchasingWorld()
    _, accountant, hj, p2 = scn04(world)
    with pytest.raises(PriceGapToConfirm):
        world.correct(accountant, p2, lines=world.line(hj, 5, 50_000))
    world.correct(accountant, p2, lines=world.line(hj, 5, 50_000), confirm=True)


def test_pur09_cancel_reverses_entries_and_replays_wac() -> None:
    world = PurchasingWorld()
    owner, accountant, hj, p2 = scn04(world)
    with pytest.raises(PermissionDenied):
        world.purchasing.cancel.execute(accountant, p2.purchase.id, "doublon")  # Q-13
    view = world.purchasing.cancel.execute(owner, p2.purchase.id, "doublon")
    assert view.purchase.status is PurchaseStatus.CANCELLED
    assert costs(world, owner, hj) == (500_000, 500_000)
    reversal = world.movements(owner, hj)[0]
    assert (reversal.type, str(reversal.quantity)) == (MovementType.REVERSAL, "-5")
    with pytest.raises(InvalidStateTransition):
        world.purchasing.cancel.execute(owner, p2.purchase.id, "encore")
    with pytest.raises(InvalidStateTransition):
        world.correct(owner, p2, note="annulé")


def test_pur10_cancel_refused_once_part_has_left() -> None:
    world = PurchasingWorld()
    owner, accountant, _, hj = world.setup()
    bought = world.buy(accountant, hj, 3, 500_000)
    world.sell(owner, hj, "Garoua", 1)
    with pytest.raises(StockAlreadyLeft):
        world.purchasing.cancel.execute(owner, bought.purchase.id, "erreur")
    only = world.buy(owner, hj, 2, 500_000)
    world.purchasing.cancel.execute(owner, only.purchase.id, "erreur")  # rien n'en est sorti
    assert costs(world, owner, hj) == (500_000, 500_000)
    world.purchasing.cancel.execute(owner, world.buy(owner, hj, 1, 1).purchase.id, "test")
    assert world.matrix_total(owner, hj) == "2"


def test_location_change_moves_stock_and_cancel_all_resets_costs() -> None:
    world = PurchasingWorld()
    owner, _, _, hj = world.setup()
    bought = world.buy(owner, hj, 4, 500_000)
    world.correct(owner, bought, location_id=world.loc(owner, "Garoua-Boulaï"))
    rows = world.stock_http.matrix.execute(owner).rows
    cells = {str(c.location_id): str(c.sellable) for c in rows[0].cells}
    assert cells[str(world.loc(owner, "Garoua-Boulaï"))] == "4"
    assert cells[str(world.loc(owner, "Garoua"))] == "0"
    world.purchasing.cancel.execute(owner, bought.purchase.id, "erreur")
    assert costs(world, owner, hj) == (None, None)  # RG-T15 : plus aucun coût connu
