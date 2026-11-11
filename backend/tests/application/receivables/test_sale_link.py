"""UC-CRE-01 et vente liée : ouverture dans la transaction de la vente (§ 17.5, SCN-01 étape 7),
modification (MOD-01), annulation (SCN-06), retour, plafond de crédit avec le vrai dû."""

from dataclasses import replace
from datetime import date

import pytest

from app.application.receivables.ports import ReceivableRepository
from app.application.receivables.sync import ReceivableSync
from app.application.receivables.use_cases.read_receivables import ReceivableCriteria
from app.application.sales.customer_input import patched_details
from app.application.sales.ports import CustomerRepository
from app.application.sales.returning import ReturnLineInput
from app.application.sales.use_cases.cancel_sale import CancelSaleCommand
from app.application.sales.use_cases.modify_sale import LinePatch, ModifySaleCommand
from app.application.sales.use_cases.record_return import ReturnCommand
from app.application.security.actor import Actor
from app.application.shops.context import performer_of
from app.domain.receivables.errors import AmountBelowPaid
from app.domain.receivables.ids import receivable_id_for_sale
from app.domain.receivables.values import ReceivableOrigin, ReceivableStatus
from app.domain.sales.errors import CreditLimitExceeded
from app.domain.sales.ids import CustomerId
from app.domain.sales.receivable_events import CreditSaleReturned
from app.domain.shared.errors import InvalidStateTransition
from app.domain.shared.money import Money
from tests.application.receivables.support import ReceivablesWorld


def test_scn01_credit_sale_opens_receivable_of_480000() -> None:
    world = ReceivablesWorld()
    _, _, seller, _, view = world.scn01()
    r = view.receivable
    assert (r.origin, r.status, r.initial_amount) == (
        ReceivableOrigin.SALE,
        ReceivableStatus.OPEN,
        Money(480_000),
    )
    assert (r.sale_total, r.paid_at_sale, r.remaining) == (
        Money(780_000),
        Money(300_000),
        Money(480_000),
    )
    assert r.responsible_seller_id == seller.user_id  # REC-01
    assert r.opened_on == date(2026, 11, 11)
    assert r.sale_number == "V-000001"
    assert view.customer.name == "Moussa A."
    assert world.get(seller, r.id).receivable.id == r.id  # siennes


def test_failed_opening_cancels_the_sale(monkeypatch: pytest.MonkeyPatch) -> None:
    world = ReceivablesWorld()
    owner, accountant, seller, hj = world.setup()
    world.buy(accountant, hj, 20, 520_000)

    def broken(self: ReceivableRepository, receivable: object) -> None:
        msg = "panne"
        raise RuntimeError(msg)

    monkeypatch.setattr(ReceivableRepository, "add", broken)
    with pytest.raises(RuntimeError, match="panne"):
        world.credit(seller, world.article(owner, hj), 780_000, 300_000)
    monkeypatch.undo()
    assert world.matrix_total(owner, hj) == "20"  # aucune sortie de stock
    second = world.credit(seller, world.article(owner, hj), 780_000, 300_000)
    assert str(second.sale.number) == "V-000001"  # aucun numéro consommé


def test_mod01_price_change_revises_receivable() -> None:
    world = ReceivablesWorld()
    owner, _, seller, _, view = world.scn01()
    sale_id = view.receivable.sale_id
    assert sale_id is not None
    patch = {"lines": (LinePatch(unit_price=760_000),)}
    command = ModifySaleCommand(sale_id=sale_id, version=1, reason="mauvais prix", patch=patch)
    world.sales.modify.execute(owner, command)
    revised = world.get(owner, view.receivable.id).receivable
    assert (revised.initial_amount, revised.sale_total) == (Money(460_000), Money(760_000))
    world.versement(seller, revised.id, 400_000)
    lower = {"lines": (LinePatch(unit_price=600_000),)}  # créance 300 000 < 400 000 versés
    refused = ModifySaleCommand(sale_id=sale_id, version=2, reason="remise", patch=lower)
    with pytest.raises(AmountBelowPaid):
        world.sales.modify.execute(owner, refused)
    sale = world.sales.get.execute(owner, sale_id).sale
    assert sale.version == 2  # la modification entière est annulée


def test_scn06_cancelled_sale_cancels_receivable_and_marks_refund() -> None:
    world = ReceivablesWorld()
    owner, _, seller, _, view = world.scn01()
    paid = world.versement(seller, view.receivable.id, 100_000, "Orange Money")
    assert str(paid.installment.number) == "R-000001"
    assert paid.view.receivable.remaining == Money(380_000)
    sale_id = view.receivable.sale_id
    assert sale_id is not None
    cancel = CancelSaleCommand(sale_id=sale_id, reason="client a renoncé", refund_payments=True)
    world.sales.cancel.execute(owner, cancel)
    r = world.get(owner, view.receivable.id).receivable
    assert r.status is ReceivableStatus.CANCELLED
    assert r.installments[0].to_refund
    assert not r.counts_as_due
    listing = world.receivables.list.execute(owner, ReceivableCriteria())
    assert listing.summary.total_due == Money(0)
    with pytest.raises(InvalidStateTransition):
        world.versement(owner, r.id, 1_000)


def test_credit_sale_returned_lowers_receivable() -> None:
    world = ReceivablesWorld()
    owner, _, _, _, view = world.scn01()
    sale_id = view.receivable.sale_id
    assert sale_id is not None
    with world.core.shop_uow_factory(world.shop_of(owner)) as uow:
        event = CreditSaleReturned(
            shop_id=uow.shop_id,
            occurred_at=world.clock.now(),
            sale_id=sale_id,
            amount=Money(80_000),
        )
        ReceivableSync().handle(event, uow)
        uow.commit()
    assert world.get(owner, view.receivable.id).receivable.initial_amount == Money(400_000)
    with world.core.shop_uow_factory(world.shop_of(owner)) as uow:  # au-delà du reste
        ReceivableSync().handle(replace(event, amount=Money(900_000)), uow)
        uow.commit()
    capped = world.get(owner, view.receivable.id).receivable
    assert (capped.remaining, capped.status) == (Money(0), ReceivableStatus.SETTLED)


def test_return_after_installment_is_capped_to_remaining() -> None:
    """780 000, acompte 300 000, versement 400 000, retour total : reste 0, jamais négatif."""
    world = ReceivablesWorld()
    owner, _, seller, _, view = world.scn01()
    world.versement(seller, view.receivable.id, 400_000)
    sale_id = view.receivable.sale_id
    assert sale_id is not None
    command = ReturnCommand(
        sale_id=sale_id,
        lines=(ReturnLineInput(line=1, quantity="1"),),
        reason="moteur bruyant",
    )
    world.sales.record_return.execute(owner, command)
    after = world.get(owner, view.receivable.id).receivable
    assert (after.initial_amount, after.total_paid) == (Money(400_000), Money(400_000))
    assert (after.remaining, after.status) == (Money(0), ReceivableStatus.SETTLED)


def test_credit_limit_uses_real_debt() -> None:
    world = ReceivablesWorld()
    owner, accountant, seller, hj = world.setup()
    world.buy(accountant, hj, 20, 520_000)
    hj = world.article(owner, hj)
    first = world.credit(seller, hj, 780_000, 300_000).sale
    customer_id = first.content.customer_id
    assert customer_id is not None
    set_limit(world, owner, customer_id, 900_000)
    with pytest.raises(CreditLimitExceeded):  # 480 000 dus + 480 000 > 900 000
        world.credit(seller, hj, 780_000, 300_000)
    world.versement(seller, receivable_id_for_sale(first.id), 100_000)  # dû 380 000
    second = world.credit(seller, hj, 780_000, 300_000)  # 380 000 + 480 000 ≤ 900 000
    assert second.sale.remaining == Money(480_000)


def set_limit(world: ReceivablesWorld, owner: Actor, customer_id: CustomerId, limit: int) -> None:
    with world.core.shop_uow_factory(world.shop_of(owner)) as uow:
        customers = CustomerRepository.within(uow)
        customer = customers.get(customer_id)
        details = patched_details(customer.details, {"credit_limit": limit})
        customer.change(details, performer=performer_of(owner), now=world.clock.now())
        customers.update(customer)
        uow.commit()
