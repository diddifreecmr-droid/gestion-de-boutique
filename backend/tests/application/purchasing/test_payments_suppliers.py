"""UC-ACH-02, 05, 06 : fournisseurs (SUP-01, SUP-02), liste et totaux (PUR-11), paiements
fournisseur (PUR-12, ERR-OVR-05)."""

from datetime import date

import pytest

from app.application.ports.pagination import PageRequest
from app.application.purchasing.resolver import PurchaseInput
from app.application.purchasing.use_cases.read_purchases import PurchaseCriteria
from app.application.purchasing.use_cases.record_payment import PaymentCommand
from app.application.purchasing.use_cases.record_purchase import RecordPurchaseCommand
from app.application.security.actor import Actor
from app.application.security.errors import PermissionDenied
from app.application.shops.ports import PaymentModeRepository
from app.domain.purchasing.errors import Overpayment
from app.domain.purchasing.ids import SupplierPaymentId
from app.domain.purchasing.lines import FeeKind
from app.domain.purchasing.payments import PaymentStatus
from app.domain.purchasing.supplier import SupplierDetails
from app.domain.shared.errors import Duplicate, InvalidStateTransition, ValidationFailed
from app.domain.shops.ids import PaymentModeId
from tests.application.purchasing.support import PurchasingWorld


def cash(world: PurchasingWorld, actor: Actor) -> PaymentModeId:
    with world.core.shop_uow_factory(world.shop_of(actor)) as uow:
        return PaymentModeRepository.within(uow).list_all()[0].id


def test_pur12_payment_status_and_overpayment() -> None:
    world = PurchasingWorld()
    owner, accountant, _, hj = world.setup()
    bought = world.buy(accountant, hj, 20, 520_000, fees=((FeeKind.CUSTOMS, 400_000, None),))
    mode = cash(world, owner)

    def pay(amount: int, payment_id: SupplierPaymentId | None = None):  # type: ignore[no-untyped-def]
        command = PaymentCommand(
            purchase_id=bought.purchase.id, amount=amount, mode_id=mode, payment_id=payment_id
        )
        return world.purchasing.pay.execute(accountant, command)

    first = SupplierPaymentId.new()
    view, created = pay(4_000_000, first)
    assert created
    assert view.purchase.payment_status is PaymentStatus.PARTIALLY_PAID
    view, created = pay(4_000_000, first)  # rejeu idempotent
    assert not created
    assert view.purchase.paid.amount == 4_000_000
    view, _ = pay(6_800_000)
    assert view.purchase.payment_status is PaymentStatus.PAID
    with pytest.raises(Overpayment):
        pay(1)  # ERR-OVR-05
    with pytest.raises(ValidationFailed):
        pay(0)
    world.purchasing.cancel.execute(owner, world.buy(owner, hj, 1, 1).purchase.id, "x")


def test_payment_refused_on_cancelled_purchase() -> None:
    world = PurchasingWorld()
    owner, _, _, hj = world.setup()
    bought = world.buy(owner, hj, 1, 500_000)
    world.purchasing.cancel.execute(owner, bought.purchase.id, "doublon")
    command = PaymentCommand(purchase_id=bought.purchase.id, amount=1, mode_id=cash(world, owner))
    with pytest.raises(InvalidStateTransition):
        world.purchasing.pay.execute(owner, command)


def test_sup01_sup02_suppliers_and_sheet() -> None:
    world = PurchasingWorld()
    owner, accountant, seller, hj = world.setup()
    suppliers = world.purchasing.suppliers
    haojue, created = suppliers.create(accountant, SupplierDetails(name="Haojue Douala"))
    assert created
    with pytest.raises(Duplicate) as clash:
        suppliers.create(owner, SupplierDetails(name=" haojue  DOUALA"))
    assert clash.value.details["constraint"] == "supplier_name"
    again, created = suppliers.create(owner, SupplierDetails(name="x"), haojue.id)
    assert (created, again.name) == (False, "Haojue Douala")
    with pytest.raises(PermissionDenied):
        suppliers.list_all(seller)
    data = PurchaseInput(lines=world.line(hj, 2, 500_000), supplier_id=haojue.id)
    world.purchasing.record.execute(accountant, RecordPurchaseCommand(data=data))
    world.buy(accountant, hj, 1, 500_000)  # sans fournisseur
    sheet = suppliers.sheet(owner, haojue.id)
    assert (len(sheet.purchases), sheet.totals.total.amount) == (1, 1_000_000)
    off = suppliers.update(owner, haojue.id, {"active": False}, haojue.version)
    assert not off.active
    assert [s.name for s in suppliers.list_all(owner)] == ["Haojue Douala"]
    with pytest.raises(ValidationFailed):  # fournisseur désactivé : plus proposé à l'achat
        world.purchasing.record.execute(accountant, RecordPurchaseCommand(data=data))
    with pytest.raises(ValueError, match="non modifiables"):
        suppliers.update(owner, haojue.id, {"id": 1}, off.version)


def test_pur11_list_filters_and_period_totals() -> None:
    world = PurchasingWorld()
    owner, accountant, _, hj = world.setup()
    yd = world.moto(owner, model="YD110")
    world.at(date(2026, 11, 3))
    world.buy(accountant, hj, 1, 500_000)
    world.at(date(2026, 11, 5))
    world.buy(accountant, yd, 2, 400_000, where="Garoua-Boulaï")
    cancelled = world.buy(owner, hj, 1, 100)
    world.purchasing.cancel.execute(owner, cancelled.purchase.id, "erreur")
    listing = world.purchasing.list.execute(accountant, PurchaseCriteria(), PageRequest())
    assert (listing.first_day, listing.last_day) == (date(2026, 11, 1), date(2026, 11, 5))
    assert [str(v.purchase.number) for v in listing.items] == ["A-000003", "A-000002", "A-000001"]
    assert (listing.totals.count, listing.totals.total.amount) == (2, 1_300_000)
    by_article = PurchaseCriteria(article_id=yd.id)
    found = world.purchasing.list.execute(owner, by_article, PageRequest()).items
    assert [str(v.purchase.number) for v in found] == ["A-000002"]
    there = PurchaseCriteria(location_id=world.loc(owner, "Garoua"), first_day=date(2026, 11, 3))
    assert len(world.purchasing.list.execute(owner, there, PageRequest()).items) == 2
    page = world.purchasing.list.execute(owner, PurchaseCriteria(), PageRequest(limit=2))
    assert page.next_cursor is not None
    inverted = PurchaseCriteria(first_day=date(2026, 11, 5), last_day=date(2026, 11, 1))
    with pytest.raises(ValidationFailed):
        world.purchasing.list.execute(owner, inverted, PageRequest())
    got = world.purchasing.get.execute(owner, cancelled.purchase.id)
    assert (got.editable, got.cancellable) == (False, False)
