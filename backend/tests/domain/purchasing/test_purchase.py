"""Agrégats `Purchase` et `Supplier` : délai du comptable (PUR-07), motif (PUR-08), paiements
(PUR-12, ERR-OVR-05), annulation (RG-T03), unicité d'un article par achat, fournisseur."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.domain.audit.values import Performer
from app.domain.catalog.ids import ArticleId
from app.domain.purchasing.errors import CorrectionWindowClosed, Overpayment, ReasonRequired
from app.domain.purchasing.ids import SupplierPaymentId
from app.domain.purchasing.lines import FeeKind, PurchaseFee, PurchaseLine, cost_lines
from app.domain.purchasing.payment_rules import add_payment
from app.domain.purchasing.payments import PaymentStatus, SupplierPayment
from app.domain.purchasing.purchase import Purchase
from app.domain.purchasing.supplier import Supplier, SupplierDetails
from app.domain.purchasing.units import EntryUnit
from app.domain.purchasing.values import Capture, PurchaseDetails
from app.domain.shared.doc_number import DocNumber, DocType
from app.domain.shared.errors import InvalidAmount, InvalidStateTransition, ValidationFailed
from app.domain.shared.ids import DeviceId, ShopId, UserId
from app.domain.shared.money import Money
from app.domain.shared.quantity import Quantity, StockUnit
from app.domain.shops.ids import LocationId, PaymentModeId

NOW = datetime(2026, 11, 10, 8, tzinfo=UTC)
PERFORMER = Performer(UserId.new(), "accountant", DeviceId.new())
ARTICLE = ArticleId.new()
LOCATION = LocationId.new()


def details(price: int = 520_000, quantity: int = 20) -> PurchaseDetails:
    line = PurchaseLine(
        article_id=ARTICLE, quantity=Decimal(quantity), unit=EntryUnit.UNIT, unit_price=Money(price)
    )
    fee = PurchaseFee(kind=FeeKind.CUSTOMS, amount=Money(400_000))
    return PurchaseDetails(
        purchase_date=date(2026, 11, 3), location_id=LOCATION, lines=(line,), fees=(fee,)
    )


def priced(data: PurchaseDetails) -> tuple[PurchaseDetails, tuple]:  # type: ignore[type-arg]
    quantities = [Quantity.of(line.quantity, StockUnit.UNIT) for line in data.lines]
    return data, cost_lines(data.lines, quantities, data.fees)


def purchase() -> Purchase:
    data, costed = priced(details())
    capture = Capture(PERFORMER.user_id, DeviceId.new(), NOW, NOW)
    return Purchase.record(
        ShopId.new(), DocNumber(DocType.PURCHASE, 1), data, costed, capture, performer=PERFORMER
    )


def payment(amount: int) -> SupplierPayment:
    return SupplierPayment(
        id=SupplierPaymentId.new(),
        paid_on=date(2026, 11, 10),
        amount=Money(amount),
        mode_id=PaymentModeId.new(),
        recorded_at=NOW,
        recorded_by=PERFORMER.user_id,
    )


def test_totals_and_payments_pur12() -> None:
    bought = purchase()
    assert (bought.merchandise_total, bought.fees_total, bought.total) == (
        Money(10_400_000),
        Money(400_000),
        Money(10_800_000),
    )
    statuses = [bought.payment_status]
    first = payment(4_000_000)
    assert add_payment(bought, first, performer=PERFORMER)
    statuses.append(bought.payment_status)
    assert not add_payment(bought, first, performer=PERFORMER)  # rejeu
    add_payment(bought, payment(6_800_000), performer=PERFORMER)
    statuses.append(bought.payment_status)
    assert statuses == [PaymentStatus.TO_PAY, PaymentStatus.PARTIALLY_PAID, PaymentStatus.PAID]
    with pytest.raises(Overpayment) as refused:
        add_payment(bought, payment(1), performer=PERFORMER)
    assert refused.value.details["remaining"] == 0
    with pytest.raises(InvalidAmount):
        payment(0)
    data, costed = priced(details(price=1))
    with pytest.raises(Overpayment):  # une correction ne descend pas sous le payé
        bought.correct(data, costed, reason="erreur", performer=PERFORMER, now=NOW)


def test_correction_window_reason_and_cancellation() -> None:
    bought = purchase()
    bought.require_correctable(by_owner=False, today=date(2026, 11, 10))  # J+7 inclus
    with pytest.raises(CorrectionWindowClosed):
        bought.require_correctable(by_owner=False, today=date(2026, 11, 11))
    bought.require_correctable(by_owner=True, today=date(2027, 1, 1))
    data, costed = priced(details(price=530_000))
    with pytest.raises(ReasonRequired):
        bought.correct(data, costed, reason="  ", performer=PERFORMER, now=NOW)
    same, same_costed = priced(details())
    assert not bought.correct(same, same_costed, reason="rien", performer=PERFORMER, now=NOW)
    assert bought.correct(data, costed, reason="faute", performer=PERFORMER, now=NOW)
    with pytest.raises(ValidationFailed):
        bought.cancel("x" * 501, performer=PERFORMER, now=NOW)
    bought.cancel("doublon", performer=PERFORMER, now=NOW)
    with pytest.raises(InvalidStateTransition):
        add_payment(bought, payment(1), performer=PERFORMER)
    with pytest.raises(InvalidStateTransition):
        bought.cancel("encore", performer=PERFORMER, now=NOW)


def test_details_guards() -> None:
    line = details().lines[0]
    with pytest.raises(ValidationFailed, match="une fois"):
        PurchaseDetails(purchase_date=date(2026, 11, 3), location_id=LocationId.new(),
                        lines=(line, line))  # fmt: skip
    with pytest.raises(ValidationFailed):
        PurchaseDetails(purchase_date=date(2026, 11, 3), location_id=LocationId.new(), lines=())
    data, costed = priced(details())
    capture = Capture(PERFORMER.user_id, DeviceId.new(), NOW, NOW)
    with pytest.raises(ValueError, match="A-"):
        Purchase.record(ShopId.new(), DocNumber(DocType.SALE, 1), data, costed, capture,
                        performer=PERFORMER)  # fmt: skip


def test_supplier_changes_and_deactivation() -> None:
    supplier = Supplier.create(
        ShopId.new(), SupplierDetails(name="  Haojue   Douala "), performer=PERFORMER, now=NOW
    )
    assert (supplier.name, supplier.name_key) == ("Haojue Douala", "haojue douala")
    assert not supplier.change(SupplierDetails(name="Haojue Douala"), performer=PERFORMER, now=NOW)
    changed = SupplierDetails(name="Haojue Douala", active=False)
    assert supplier.change(changed, performer=PERFORMER, now=NOW)
    assert not supplier.active
    with pytest.raises(ValidationFailed):
        SupplierDetails(name=" ")
