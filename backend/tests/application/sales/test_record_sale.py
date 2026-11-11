"""UC-VEN-01 / 02 — Enregistrer une vente : SCN-01 étape 7 (§ 17.5), coût inconnu (RG-T15),
paiements (SAL-01, ERR-OVR-02/03, Q-12), crédit (SAL-07, ERR-CRD-01 à 04), numéros continus
(RG-T05) ; prix minimum : `test_min_price_rules.py`."""

import pytest

from app.application.audit.ports import AuditQuery
from app.application.sales.inputs import CustomerInput
from app.application.security.actor import Actor
from app.domain.catalog.article import Article
from app.domain.purchasing.lines import FeeKind
from app.domain.sales.errors import (
    CreditLimitExceeded,
    CustomerRequired,
    PaymentIncomplete,
    SaleOverpayment,
)
from app.domain.sales.values import SaleKind
from app.domain.shared.money import Money
from tests.application.sales.support import MOUSSA, SalesWorld

type Bought = tuple[SalesWorld, Actor, Actor, Actor, Article]


def bought() -> Bought:
    """SCN-01 étape 1 : 20 HJ à 520 000 + douane 400 000 → coût unitaire 540 000 à Garoua."""
    world = SalesWorld()
    owner, accountant, seller, hj = world.setup()
    world.buy(accountant, hj, 20, 520_000, fees=((FeeKind.CUSTOMS, 400_000, None),))
    return world, owner, accountant, seller, world.article(owner, hj)


def test_scn01_credit_sale_of_780000_with_300000_deposit() -> None:
    world, owner, _, seller, hj = bought()
    view = world.credit(seller, hj, 780_000, 300_000)
    sale = view.sale
    assert (str(sale.number), sale.total, sale.paid, sale.remaining) == (
        "V-000001",
        Money(780_000),
        Money(300_000),
        Money(480_000),
    )
    line = sale.content.lines[0]
    assert (line.frozen_last_cost, line.frozen_wac) == (Money(540_000), Money(540_000))
    assert (line.margin, line.margin_wac) == (Money(240_000), Money(240_000))
    assert not view.show_costs  # vue du vendeur : aucun coût (SEC-N01)
    assert world.matrix_total(owner, hj) == "19"
    moves = world.movements(owner, hj)
    assert (moves[0].type.label, str(moves[0].quantity)) == ("Sortie vente", "-1")
    journal = world.journal(world.shop_of(seller), AuditQuery(modules={"sales"}))
    assert {e.entity.type for e in journal} == {"sale", "customer"}


def test_unknown_cost_margin_not_computable_and_numbers_continue() -> None:
    world = SalesWorld()
    owner, _, seller, hj = world.setup()
    world.stock_in(owner, hj, "Garoua", 3)
    world.set_costs(owner, hj, None, None)
    first = world.cash(seller, hj, 780_000).sale
    assert first.content.lines[0].margin is None  # RG-T15
    second = world.cash(owner, hj, 790_000).sale
    assert [str(first.number), str(second.number)] == ["V-000001", "V-000002"]


def test_multi_payment_overpayment_and_incomplete_cash() -> None:
    world, _, _, seller, hj = bought()
    two = world.line(hj, 250_000, 2)
    payments = world.pay(seller, ("Espèces", 300_000), ("Orange Money", 200_000))
    view, _ = world.record(seller, two, payments=payments)
    assert [p.amount.amount for p in view.sale.content.payments] == [300_000, 200_000]  # SAL-01
    one = world.line(hj, 780_000)
    over = world.pay(seller, ("Espèces", 500_000), ("Orange Money", 300_000))
    with pytest.raises(SaleOverpayment):  # ERR-OVR-02
        world.record(seller, one, payments=over)
    with pytest.raises(PaymentIncomplete):  # Q-12
        world.record(seller, one, payments=world.pay(seller, ("Espèces", 500_000)))
    with pytest.raises(SaleOverpayment):  # ERR-OVR-03
        world.record(
            seller,
            one,
            kind=SaleKind.CREDIT,
            customer=MOUSSA,
            payments=world.pay(seller, ("Espèces", 800_000)),
        )


def test_credit_customer_required_and_credit_limit() -> None:
    world, owner, _, seller, hj = bought()
    one = world.line(hj, 780_000)
    with pytest.raises(CustomerRequired):  # SAL-07
        world.record(seller, one, kind=SaleKind.CREDIT, payments=())
    zero = world.credit(seller, hj, 780_000, 0)  # acompte 0 accepté
    customer_id = zero.sale.content.customer_id
    assert customer_id is not None
    world.sales.customers.update(owner, customer_id, {"credit_limit": 1_000_000}, 1)
    known = CustomerInput(customer_id=customer_id)
    small = world.line(hj, 400_000)
    deposit = world.pay(seller, ("Espèces", 100_000))
    with pytest.raises(CreditLimitExceeded) as refused:  # 780 000 + 300 000 > 1 000 000
        world.record(seller, small, kind=SaleKind.CREDIT, customer=known, payments=deposit)
    assert refused.value.details["due_after"] == 1_080_000
    enough = world.pay(seller, ("Espèces", 180_000))
    exact, _ = world.record(seller, small, kind=SaleKind.CREDIT, customer=known, payments=enough)
    assert exact.warnings == ()  # égalité acceptée (Q-45, ERR-CRD-02)
    warned, _ = world.record(owner, small, kind=SaleKind.CREDIT, customer=known, payments=())
    assert [w.code for w in warned.warnings] == ["CREDIT_LIMIT_EXCEEDED"]  # ERR-CRD-03


def test_quick_customer_is_merged_by_phone() -> None:
    world, _, _, seller, hj = bought()
    first = world.credit(seller, hj, 780_000, 0)
    twin = CustomerInput(name="Autre nom", phone="690 00 00 00")
    line = world.line(hj, 700_000)
    again, _ = world.record(seller, line, kind=SaleKind.CREDIT, customer=twin, payments=())
    assert again.sale.content.customer_id == first.sale.content.customer_id  # UC-VEN-10
