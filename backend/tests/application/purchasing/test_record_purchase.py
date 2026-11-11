"""UC-ACH-01 par la composition root : SCN-01 étape 1 (540 000), SCN-02 (CMP 510 000), PUR-02
(avertissement > 30 %), lieu par défaut (Q-01), textile en yards (RG-X02), idempotence, droits."""

from datetime import date

import pytest

from app.application.audit.ports import AuditQuery
from app.application.catalog.use_cases.context import ArticleInput
from app.application.catalog.use_cases.create_article import CreateArticleCommand
from app.application.purchasing.resolver import LineInput, PurchaseInput
from app.application.purchasing.use_cases.record_purchase import RecordPurchaseCommand
from app.application.security.errors import PermissionDenied
from app.domain.audit.values import AuditAction
from app.domain.purchasing.errors import PriceGapToConfirm
from app.domain.purchasing.ids import PurchaseId
from app.domain.purchasing.lines import FeeKind
from app.domain.purchasing.payments import PaymentStatus
from app.domain.purchasing.units import EntryUnit
from app.domain.shared.errors import DateOutOfRange, InvalidQuantity, ValidationFailed
from app.domain.shared.money import Money
from app.domain.shared.roles import Role
from app.domain.stock.values import MovementType
from tests.application.purchasing.support import PurchasingWorld, costs

NOV = date(2026, 11, 1)


def day(n: int) -> date:
    return NOV.replace(day=n)


def test_scn01_twenty_motos_with_customs() -> None:
    world = PurchasingWorld()
    owner, accountant, _, hj = world.setup()
    world.at(day(10))
    view = world.buy(
        accountant, hj, 20, 520_000, fees=((FeeKind.CUSTOMS, 400_000, None),), confirm=False
    )
    bought = view.purchase
    assert str(bought.number) == "A-000001"
    assert (bought.merchandise_total.amount, bought.fees_total.amount, bought.total.amount) == (
        10_400_000,
        400_000,
        10_800_000,
    )
    [line] = bought.costed
    assert (line.fee_share.amount, line.unit_cost.amount) == (400_000, 540_000)
    assert costs(world, owner, hj) == (540_000, 540_000)
    assert world.matrix_total(owner, hj) == "20"
    [move] = world.movements(owner, hj)
    assert (move.type, str(move.quantity), str(move.balance_after)) == (
        MovementType.PURCHASE_IN,
        "20",
        "20",
    )
    assert move.unit_cost is not None
    assert move.unit_cost.amount == 540_000
    assert bought.payment_status is PaymentStatus.TO_PAY
    entries = world.journal(world.shop_of(owner), AuditQuery(entity_type="purchase"))
    assert [e.action for e in entries] == [AuditAction.CREATE]
    assert (view.editable, view.cancellable) == (True, False)


def test_scn02_wac_510000_and_stock_value() -> None:
    world = PurchasingWorld()
    owner, _, _, hj = world.setup()
    world.at(day(1))
    world.buy(owner, hj, 10, 500_000)
    assert costs(world, owner, hj) == (500_000, 500_000)
    world.at(day(2))
    world.buy(owner, hj, 5, 530_000)
    assert costs(world, owner, hj) == (530_000, 510_000)
    assert world.matrix_total(owner, hj) == "15"
    value = world.stock_http.value.execute(owner)
    assert value.sellable.at_wac is not None
    assert value.sellable.at_wac.amount == 7_650_000
    assert value.sellable.at_last_cost == Money(7_950_000)  # vue dernier coût


def test_pur02_price_gap_warning_over_thirty_percent() -> None:
    world = PurchasingWorld()
    owner, accountant, _, hj = world.setup()
    world.buy(owner, hj, 1, 520_000)
    for price in (52_000, 363_999, 676_001):
        with pytest.raises(PriceGapToConfirm) as warned:
            world.buy(accountant, hj, 1, price, confirm=False)
        lines = warned.value.details["lines"]
        assert lines == [
            {"line": 0, "article_id": str(hj.id), "last_cost": 520_000, "unit_price": price}
        ]
    world.buy(accountant, hj, 1, 364_000, confirm=False)  # -30 % exact : pas de message
    world.buy(accountant, hj, 1, 52_000, confirm=True)
    assert world.matrix_total(owner, hj) == "3"


def test_default_reception_location_and_idempotence() -> None:
    world = PurchasingWorld()
    owner, _, _, hj = world.setup()
    wanted = PurchaseId.new()
    command = RecordPurchaseCommand(
        data=PurchaseInput(lines=world.line(hj, 2, 500_000)), purchase_id=wanted
    )
    view, created = world.purchasing.record.execute(owner, command)
    assert created
    assert view.purchase.details.location_id == world.loc(owner, "Garoua")
    again, created = world.purchasing.record.execute(owner, command)
    assert (created, again.purchase.number) == (False, view.purchase.number)
    assert world.matrix_total(owner, hj) == "2"  # aucun second mouvement


def test_rights_dates_and_input_errors() -> None:
    world = PurchasingWorld()
    owner, accountant, seller, hj = world.setup()
    driver = world.staff(owner, Role.DRIVER)
    for who in (seller, driver):
        with pytest.raises(PermissionDenied):
            world.buy(who, hj, 1, 1)
    world.at(day(10))
    with pytest.raises(DateOutOfRange):
        world.buy(accountant, hj, 1, 500_000, on=day(2))  # J-8 (RG-T09)
    world.buy(accountant, hj, 1, 500_000, on=day(3))  # J-7
    world.buy(owner, hj, 1, 500_000, on=date(2026, 1, 5))  # propriétaire : illimité
    for quantity in ("0", "-1", "1.5"):
        with pytest.raises(InvalidQuantity):
            world.buy(owner, hj, quantity, 500_000)  # PUR-04
    with pytest.raises(ValidationFailed):
        world.buy(owner, hj, 1, 500_000, fees=((FeeKind.OTHER, 1_000, None),))  # SCN-03 d
    with pytest.raises(ValidationFailed):
        world.buy(owner, hj, 1, 500_000, unit=EntryUnit.YARD)  # unité incompatible


def test_textile_bought_in_yards_cost_per_meter() -> None:
    world = PurchasingWorld()
    owner = world.open_profile("textile")
    command = CreateArticleCommand(data=ArticleInput(fields={"name": "Wax", "unit": "METER"}))
    wax, _ = world.catalog.create.execute(owner, command)
    store = world.location_id(world.shop_of(owner), "Boutique")
    data = PurchaseInput(
        lines=(LineInput(article_id=wax.id, quantity="10", unit_price=1_000, unit=EntryUnit.YARD),),
        location_id=store,
    )
    view, _ = world.purchasing.record.execute(owner, RecordPurchaseCommand(data=data))
    [line] = view.purchase.costed
    assert (str(line.stock_quantity), line.total.amount, line.unit_cost.amount) == (
        "9.1",
        10_000,
        1_099,
    )  # 10 yd → 9,1 m ; 10 000 / 9,1 = 1 098,9 → 1 099 F/m
    assert costs(world, owner, wax) == (1_099, 1_099)
