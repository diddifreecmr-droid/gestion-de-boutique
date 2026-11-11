"""UC-VEN-07 / 08 — Modifier (MOD-01, MOD-02) et annuler une vente (SCN-06) ; coûts figés après
une correction d'achat (SCN-04 variante 2, RG-T13) ; totaux du jour (Q-09)."""

from datetime import date
from decimal import Decimal

import pytest

from app.application.ports.pagination import PageRequest
from app.application.purchasing.resolver import LineInput as PurchaseLine
from app.application.purchasing.use_cases.read_purchases import PurchaseCriteria
from app.application.sales.search import SaleCriteria
from app.application.sales.use_cases.cancel_sale import CancelSaleCommand
from app.application.sales.use_cases.modify_sale import LinePatch, ModifySaleCommand
from app.application.security.errors import PermissionDenied
from app.domain.purchasing.errors import ReasonRequired
from app.domain.sales.errors import LineChangeRefused
from app.domain.sales.values import SaleStatus
from app.domain.shared.errors import InvalidStateTransition, VersionConflict
from app.domain.shared.money import Money
from tests.application.sales.test_record_sale import bought


def test_mod01_price_change_keeps_frozen_costs() -> None:
    world, owner, accountant, seller, hj = bought()
    view = world.credit(seller, hj, 780_000, 300_000)
    sale_id = view.sale.id
    purchase = world.purchasing.list.execute(owner, _all(), PageRequest()).items[0]
    lines = (PurchaseLine(article_id=hj.id, quantity=20, unit_price=600_000),)
    world.correct(accountant, purchase, lines=lines)  # coût courant 620 000 désormais
    assert world.article(owner, hj).last_cost == Money(620_000)
    patch = {"lines": (LinePatch(unit_price=760_000),)}
    command = ModifySaleCommand(sale_id=sale_id, version=1, reason="mauvais prix", patch=patch)
    with pytest.raises(PermissionDenied):  # MOD-02 : vendeur → 403
        world.sales.modify.execute(seller, command)
    changed = world.sales.modify.execute(owner, command)
    line = changed.sale.content.lines[0]
    assert (line.frozen_last_cost, line.margin) == (Money(540_000), Money(220_000))
    assert changed.sale.remaining == Money(460_000)  # créance 480 000 → 460 000 (T17)
    assert changed.show_costs
    assert changed.sale.version == 2
    with pytest.raises(VersionConflict):
        world.sales.modify.execute(owner, command)
    for wrong in (
        {"lines": (LinePatch(quantity=Decimal(2)),)},
        {"lines": (LinePatch(), LinePatch())},
    ):
        refused = ModifySaleCommand(sale_id=sale_id, version=2, reason="x", patch=wrong)
        with pytest.raises(LineChangeRefused):
            world.sales.modify.execute(owner, refused)
    blank = ModifySaleCommand(sale_id=sale_id, version=2, reason=" ", patch=patch)
    with pytest.raises(ReasonRequired):
        world.sales.modify.execute(owner, blank)


def _all() -> PurchaseCriteria:
    return PurchaseCriteria(first_day=date(2026, 1, 1))


def test_modify_details_payments_note_and_date() -> None:
    world, owner, _, seller, hj = bought()
    sale = world.cash(seller, hj, 780_000, "LBX1").sale
    from app.domain.sales.lines import SoldDetail

    patch = {
        "lines": (LinePatch(details=(SoldDetail(chassis_number="LBX2"),)),),
        "payments": world.pay(owner, ("Espèces", 480_000), ("Orange Money", 300_000)),
        "note": "corrigée",
        "sold_on": date(2026, 11, 10),
        "customer": None,
    }
    changed = world.sales.modify.execute(
        owner, ModifySaleCommand(sale_id=sale.id, version=1, reason="saisie", patch=patch)
    ).sale
    assert changed.content.note == "corrigée"
    assert len(changed.content.payments) == 2
    world.cash(seller, hj, 780_000, "LBX1")  # l'ancien châssis est libéré


def test_scn06_cancel_restores_stock_and_counts_on_cancel_day() -> None:
    world, owner, _, seller, hj = bought()
    sale = world.credit(seller, hj, 780_000, 300_000, "LBX123").sale
    command = CancelSaleCommand(sale_id=sale.id, reason="client a renoncé", refund_payments=True)
    with pytest.raises(PermissionDenied):  # SCN-06 étape 3
        world.sales.cancel.execute(seller, command)
    cancelled = world.sales.cancel.execute(owner, command).sale
    assert cancelled.status is SaleStatus.CANCELLED
    assert world.matrix_total(owner, hj) == "20"  # « Annulation » +1
    with pytest.raises(InvalidStateTransition):  # étape 7
        world.sales.cancel.execute(owner, command)
    listing = world.sales.list.execute(owner, SaleCriteria(), PageRequest())
    assert [v.sale.status for v in listing.items] == [SaleStatus.CANCELLED]  # étape 9
    assert (listing.totals.count, listing.totals.total) == (0, Money(0))  # étape 6
    later = world.cash(seller, hj, 700_000)
    world.at(date(2026, 11, 12))
    world.sales.cancel.execute(owner, CancelSaleCommand(sale_id=later.sale.id, reason="x"))
    past = world.sales.list.execute(owner, SaleCriteria(last_day=date(2026, 11, 11)), PageRequest())
    assert past.totals.total == Money(700_000)  # une journée passée ne change pas (Q-09)
    today = world.sales.list.execute(owner, SaleCriteria(), PageRequest())
    assert (today.totals.count, today.totals.total) == (-1, Money(-700_000))
