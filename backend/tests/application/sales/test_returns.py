"""UC-VEN-09 — Retours (SCN-05, EXC-02) : partiel puis total, état Abîmé, remboursement ≤ payé,
vente à crédit (baisse de créance), vente annulée, châssis rendu revendable, portée."""

from datetime import date

import pytest

from app.application.sales.returning import RefundInput, ReturnLineInput
from app.application.sales.use_cases.cancel_sale import CancelSaleCommand
from app.application.sales.use_cases.record_return import ReturnCommand
from app.application.security.actor import Actor
from app.application.security.errors import PermissionDenied
from app.domain.sales.errors import ChassisAlreadySold, RefundOverpayment, ReturnExceedsSold
from app.domain.sales.ids import SaleId, SaleReturnId
from app.domain.shared.errors import InvalidStateTransition, ValidationFailed
from app.domain.shared.money import Money
from app.domain.stock.values import StockCondition
from tests.application.sales.support import SalesWorld
from tests.application.sales.test_record_sale import bought

J, J1 = date(2026, 11, 12), date(2026, 11, 13)


def give_back(  # type: ignore[no-untyped-def]
    world: SalesWorld,
    owner: Actor,
    sale_id: SaleId,
    quantity: str = "1",
    *,
    refund: int | None = None,
    condition: StockCondition = StockCondition.SELLABLE,
    chassis: tuple[str, ...] = (),
    return_id: SaleReturnId | None = None,
):
    command = ReturnCommand(
        sale_id=sale_id,
        lines=(ReturnLineInput(line=1, quantity=quantity, condition=condition, chassis=chassis),),
        reason="moteur bruyant",
        refund=None if refund is None else RefundInput(amount=refund, mode_id=world.mode(owner)),
        return_id=return_id,
    )
    return world.sales.record_return.execute(owner, command)


def test_scn05_partial_then_total_return() -> None:
    world, owner, _, seller, hj = bought()
    world.at(J)
    sold, _ = world.record(seller, world.line(hj, 780_000, 2))
    assert world.matrix_total(owner, hj) == "18"
    world.at(J1)
    rid = SaleReturnId.new()
    view, created = give_back(world, owner, sold.sale.id, refund=780_000, return_id=rid)
    made = view.sale_return
    assert created
    assert view.show_costs
    assert (made.amount, made.margin, made.refunded) == (
        Money(780_000),
        Money(240_000),
        Money(780_000),
    )
    assert made.returned_on == J1
    assert made.credit_reduction == Money(0)
    assert world.matrix_total(owner, hj) == "19"
    moves = world.movements(owner, hj)
    assert (moves[0].type.label, str(moves[0].quantity)) == ("Retour client", "1")
    again, replayed = give_back(world, owner, sold.sale.id, refund=780_000, return_id=rid)
    assert not replayed
    assert again.sale_return.id == rid
    with pytest.raises(ReturnExceedsSold) as exceeded:  # EXC-02
        give_back(world, owner, sold.sale.id, "2")
    assert exceeded.value.details == {"line": 1, "returnable": "1"}
    with pytest.raises(RefundOverpayment):  # 780 000 déjà remboursés sur 1 560 000 payés
        give_back(world, owner, sold.sale.id, refund=780_001)
    give_back(world, owner, sold.sale.id, refund=780_000)
    listing = world.sales.list_returns.execute(owner, sold.sale.id)
    assert [str(b.returnable) for b in listing.balances] == ["0"]
    assert [r.sale_return.amount for r in listing.returns] == [Money(780_000)] * 2
    assert world.matrix_total(owner, hj) == "20"


def test_damaged_return_keeps_sellable_stock() -> None:
    world, owner, _, seller, hj = bought()
    sold = world.cash(seller, hj, 780_000)
    give_back(world, owner, sold.sale.id, condition=StockCondition.DAMAGED)
    assert world.matrix_total(owner, hj) == "19"  # vendable inchangé
    entry = world.movements(owner, hj)[0]
    assert (entry.condition, str(entry.quantity)) == (StockCondition.DAMAGED, "1")


def test_credit_sale_return_lowers_receivable() -> None:
    world, owner, _, seller, hj = bought()
    sold = world.credit(seller, hj, 780_000, 300_000).sale  # reste 480 000
    with pytest.raises(RefundOverpayment) as over:
        give_back(world, owner, sold.id, refund=300_001)
    assert over.value.details["max"] == 300_000
    view, _ = give_back(world, owner, sold.id, refund=300_000)
    assert view.sale_return.credit_reduction == Money(480_000)
    assert view.sale_return.refunded == Money(300_000)


def test_cancelled_sale_and_cancel_after_return_refused() -> None:
    world, owner, _, seller, hj = bought()
    first = world.cash(seller, hj, 780_000).sale
    world.sales.cancel.execute(owner, CancelSaleCommand(sale_id=first.id, reason="doublon"))
    with pytest.raises(InvalidStateTransition):
        give_back(world, owner, first.id)
    second = world.cash(seller, hj, 780_000).sale
    give_back(world, owner, second.id)
    with pytest.raises(InvalidStateTransition) as refused:
        world.sales.cancel.execute(owner, CancelSaleCommand(sale_id=second.id, reason="x"))
    assert refused.value.details == {"returns": 1}


def test_returned_chassis_can_be_sold_again() -> None:
    world, owner, _, seller, hj = bought()
    sold, _ = world.record(seller, world.line(hj, 780_000, 2, "LBX 1", "LBX 2"))
    with pytest.raises(ValidationFailed):  # ligne partielle : préciser le châssis
        give_back(world, owner, sold.sale.id)
    view, _ = give_back(world, owner, sold.sale.id, chassis=("lbx-2",))
    assert view.sale_return.lines[0].chassis == ("LBX2",)
    world.cash(seller, hj, 780_000, "LBX2")  # libéré : revendable
    with pytest.raises(ChassisAlreadySold):  # toujours tenu par la vente d'origine
        world.cash(seller, hj, 780_000, "LBX1")


def test_scope_seller_reads_own_returns_without_costs() -> None:
    world, owner, accountant, seller, hj = bought()
    sold = world.cash(seller, hj, 780_000).sale
    with pytest.raises(PermissionDenied):
        give_back(world, seller, sold.id)
    give_back(world, owner, sold.id)
    listing = world.sales.list_returns.execute(seller, sold.id)
    assert [r.show_costs for r in listing.returns] == [False]
    with pytest.raises(PermissionDenied):
        world.sales.list_returns.execute(accountant, sold.id)
