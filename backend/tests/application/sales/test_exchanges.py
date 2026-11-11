"""UC-VEN-09 — Échanges (EXC-01) : seule la différence est payée ou rendue ; vente à crédit ;
la vente d'origine ne se modifie plus après un retour."""

import pytest

from app.application.sales.inputs import SaleInput
from app.application.sales.returning import ReturnLineInput
from app.application.sales.use_cases.modify_sale import ModifySaleCommand
from app.application.sales.use_cases.record_return import ExchangeInput, ReturnCommand
from app.application.sales.views import SaleView
from app.application.security.actor import Actor
from app.domain.catalog.article import Article
from app.domain.sales.ids import SaleId
from app.domain.sales.values import SaleKind
from app.domain.shared.errors import InvalidStateTransition
from app.domain.shared.money import Money
from tests.application.sales.support import SalesWorld
from tests.application.sales.test_record_sale import bought


def sym(world: SalesWorld, owner: Actor) -> Article:
    article = world.moto(owner, "Sym", "Sym", base_price=800_000)
    world.buy(owner, article, 3, 550_000)
    return world.article(owner, article)


def exchange(  # type: ignore[no-untyped-def]
    world: SalesWorld, owner: Actor, sale_id: SaleId, new: Article, price: int, paid: int
):
    data = SaleInput(
        kind=SaleKind.CASH,
        lines=(world.line(new, price),),
        payments=world.pay(owner, ("Espèces", paid)) if paid else (),
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
    return view.sale_return, view.exchange


def amounts(view: SaleView) -> list[int]:
    return [p.amount.amount for p in view.sale.content.payments]


def test_exc01_only_the_difference_is_paid() -> None:
    world, owner, _, seller, hj = bought()
    other = sym(world, owner)
    sold = world.cash(seller, hj, 780_000).sale
    made, new = exchange(world, owner, sold.id, other, 800_000, 20_000)
    assert made.exchange_sale_id == new.sale.id
    assert made.kind.value == "exchange"
    assert made.refunded == Money(780_000)  # avoir rendu dans le mode choisi…
    assert amounts(new) == [20_000, 780_000]  # … et versé à la nouvelle vente
    assert new.sale.location_id == sold.location_id
    assert world.matrix_total(owner, hj) == "20"
    assert world.matrix_total(owner, other) == "2"
    labels = [m.type.label for m in world.movements(owner, other)]
    assert labels[0] == "Sortie vente"
    assert world.movements(owner, hj)[0].type.label == "Retour client"


def test_cheaper_exchange_gives_the_difference_back() -> None:
    world, owner, _, seller, hj = bought()
    other = sym(world, owner)
    sold = world.cash(seller, hj, 780_000).sale
    made, new = exchange(world, owner, sold.id, other, 700_000, 0)
    assert amounts(new) == [700_000]
    assert made.refunded - new.sale.paid == Money(80_000)  # rendus au client


def test_exchange_on_credit_sale_lowers_receivable_first() -> None:
    world, owner, _, seller, hj = bought()
    other = sym(world, owner)
    sold = world.credit(seller, hj, 780_000, 300_000).sale
    made, new = exchange(world, owner, sold.id, other, 800_000, 500_000)
    assert made.credit_reduction == Money(480_000)
    assert made.refunded == Money(300_000)
    assert amounts(new) == [500_000, 300_000]


def test_sale_with_return_cannot_be_modified() -> None:
    world, owner, _, seller, hj = bought()
    other = sym(world, owner)
    sold = world.cash(seller, hj, 780_000).sale
    exchange(world, owner, sold.id, other, 800_000, 20_000)
    command = ModifySaleCommand(sale_id=sold.id, version=1, reason="note", patch={"note": "x"})
    with pytest.raises(InvalidStateTransition):
        world.sales.modify.execute(owner, command)
