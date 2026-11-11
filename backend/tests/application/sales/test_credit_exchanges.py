"""Échange à crédit (UC-VEN-09 ; décision client specs § 15.1) : client de la vente d'origine,
différence non payée = créance (`CreditSaleRecorded` → module Créances), plafond de crédit."""

import pytest

from app.application.sales.inputs import CustomerInput, PaymentInput, SaleInput
from app.application.sales.returning import ReturnLineInput
from app.application.sales.use_cases.record_return import ExchangeInput, ReturnCommand
from app.application.sales.views import SaleView
from app.application.security.actor import Actor
from app.domain.catalog.article import Article
from app.domain.purchasing.lines import FeeKind
from app.domain.receivables.ids import receivable_id_for_sale
from app.domain.sales.errors import CustomerRequired
from app.domain.sales.ids import SaleId
from app.domain.sales.values import SaleKind
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.money import Money
from tests.application.receivables.support import ReceivablesWorld
from tests.application.sales.support import MOUSSA

type World = tuple[ReceivablesWorld, Actor, Actor, Article, Article]


def world_with_two_motos() -> World:
    """HJ (vendue 780 000) et Sym (900 000) en stock à Garoua."""
    world = ReceivablesWorld()
    owner, accountant, seller, hj = world.setup()
    world.buy(accountant, hj, 5, 520_000, fees=((FeeKind.CUSTOMS, 100_000, None),))
    sym = world.moto(owner, "Sym", "Sym", base_price=900_000)
    world.buy(owner, sym, 3, 600_000)
    return world, owner, seller, world.article(owner, hj), world.article(owner, sym)


def sold_to_moussa(world: ReceivablesWorld, seller: Actor, hj: Article) -> SaleId:
    view, _ = world.record(seller, world.line(hj, 780_000), customer=MOUSSA)
    return view.sale.id


def exchange_on_credit(
    world: ReceivablesWorld,
    owner: Actor,
    sale_id: SaleId,
    new: Article,
    *,
    deposit: tuple[PaymentInput, ...] = (),
    customer: CustomerInput | None = None,
) -> SaleView:
    data = SaleInput(
        kind=SaleKind.CREDIT,
        lines=(world.line(new, 900_000),),
        payments=deposit,
        customer=customer,
    )
    command = ReturnCommand(
        sale_id=sale_id,
        lines=(ReturnLineInput(line=1, quantity=1),),
        reason="change de modèle",
        exchange=ExchangeInput(sale=data, mode_id=world.mode(owner)),
    )
    view, created = world.sales.record_return.execute(owner, command)
    assert created
    assert view.exchange is not None
    return view.exchange


def test_credit_exchange_780000_to_900000_deposit_0_opens_receivable_of_120000() -> None:
    world, owner, seller, hj, sym = world_with_two_motos()
    sale_id = sold_to_moussa(world, seller, hj)
    new = exchange_on_credit(world, owner, sale_id, sym)
    origin = world.sales.get.execute(owner, sale_id).sale
    assert new.sale.kind is SaleKind.CREDIT
    assert new.sale.content.customer_id == origin.content.customer_id  # client imposé
    assert (new.sale.paid, new.sale.remaining) == (Money(780_000), Money(120_000))
    receivable = world.receivables.get.execute(owner, receivable_id_for_sale(new.sale.id))
    assert receivable.receivable.initial_amount == Money(120_000)


def test_credit_exchange_with_deposit() -> None:
    world, owner, seller, hj, sym = world_with_two_motos()
    sale_id = sold_to_moussa(world, seller, hj)
    deposit = world.pay(owner, ("Espèces", 20_000))
    new = exchange_on_credit(world, owner, sale_id, sym, deposit=deposit)
    assert new.sale.remaining == Money(100_000)


def test_credit_exchange_without_customer_is_refused() -> None:
    world, owner, seller, hj, sym = world_with_two_motos()
    anonymous = world.cash(seller, hj, 780_000).sale.id
    with pytest.raises(CustomerRequired):
        exchange_on_credit(world, owner, anonymous, sym)
    assert world.matrix_total(owner, hj) == "4"  # rien n'est enregistré (retour annulé)


def test_credit_exchange_for_another_customer_is_refused() -> None:
    world, owner, seller, hj, sym = world_with_two_motos()
    sale_id = sold_to_moussa(world, seller, hj)
    other = CustomerInput(name="Awa", phone="+237699999999")
    with pytest.raises(ValidationFailed) as refused:
        exchange_on_credit(world, owner, sale_id, sym, customer=other)
    assert refused.value.details == {"field": "exchange.sale.customer"}


def test_credit_exchange_checks_the_credit_limit() -> None:
    world, owner, seller, hj, sym = world_with_two_motos()
    sale_id = sold_to_moussa(world, seller, hj)
    customer_id = world.sales.get.execute(owner, sale_id).sale.content.customer_id
    assert customer_id is not None
    world.sales.customers.update(owner, customer_id, {"credit_limit": 100_000}, 1)
    new = exchange_on_credit(world, owner, sale_id, sym)  # propriétaire : avertissement
    assert [w.code for w in new.warnings] == ["CREDIT_LIMIT_EXCEEDED"]
    assert new.warnings[0].details["due_after"] == 120_000
