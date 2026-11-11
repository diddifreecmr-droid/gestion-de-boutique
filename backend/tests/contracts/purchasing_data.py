"""Données de contrat des achats : fournisseur et achat chiffré, construits par le domaine."""

from datetime import date
from decimal import Decimal

from app.domain.audit.values import Performer
from app.domain.catalog.ids import ArticleId, AttachmentId
from app.domain.purchasing.ids import SupplierId, SupplierPaymentId
from app.domain.purchasing.lines import FeeKind, PurchaseFee, PurchaseLine, cost_lines
from app.domain.purchasing.payments import SupplierPayment
from app.domain.purchasing.purchase import Purchase
from app.domain.purchasing.supplier import Supplier, SupplierDetails
from app.domain.purchasing.units import EntryUnit
from app.domain.purchasing.values import Capture, PurchaseDetails
from app.domain.shared.doc_number import DocNumber, DocType
from app.domain.shared.ids import DeviceId, ShopId, UserId
from app.domain.shared.money import Money
from app.domain.shared.quantity import Quantity, StockUnit
from app.domain.shops.ids import LocationId, PaymentModeId
from tests.contracts.catalog_data import NOW

DEVICE = DeviceId.new()
WHO = Performer(UserId.new(), "owner", DEVICE)


def supplier(shop_id: ShopId, name: str = "Haojue Douala") -> Supplier:
    details = SupplierDetails(name=name, phone="690000000", city="Douala", country="Cameroun")
    return Supplier.create(shop_id, details, performer=WHO, now=NOW)


def purchase(
    shop_id: ShopId,
    sequence: int,
    *,
    on: date = date(2026, 11, 10),
    supplier_id: SupplierId | None = None,
    location_id: LocationId | None = None,
) -> Purchase:
    lines = (
        PurchaseLine(article_id=ArticleId.new(), quantity=Decimal(2), unit=EntryUnit.UNIT,
                     unit_price=Money(600_000)),
        PurchaseLine(article_id=ArticleId.new(), quantity=Decimal(10), unit=EntryUnit.YARD,
                     unit_price=Money(1_000)),
    )  # fmt: skip
    fees = (
        PurchaseFee(kind=FeeKind.TRANSPORT, amount=Money(100_000)),
        PurchaseFee(kind=FeeKind.OTHER, amount=Money(5_000), label="Manutention port"),
    )
    details = PurchaseDetails(
        purchase_date=on,
        location_id=location_id or LocationId.new(),
        lines=lines,
        fees=fees,
        supplier_id=supplier_id,
        invoice_ref="FAC-12",
        invoice_photo_id=AttachmentId.new(),
        note="Lot de novembre",
    )
    quantities = [Quantity.of(2, StockUnit.UNIT), Quantity.of("9.1", StockUnit.METER)]
    capture = Capture(WHO.user_id, DEVICE, NOW, NOW)
    return Purchase.record(
        shop_id,
        DocNumber(DocType.PURCHASE, sequence),
        details,
        cost_lines(lines, quantities, fees),
        capture,
        performer=WHO,
    )


def payment(amount: int) -> SupplierPayment:
    return SupplierPayment(
        id=SupplierPaymentId.new(),
        paid_on=date(2026, 11, 10),
        amount=Money(amount),
        mode_id=PaymentModeId.new(),
        recorded_at=NOW,
        recorded_by=WHO.user_id,
        reference="OM-77",
    )


def same(left: Purchase, right: Purchase) -> bool:
    return (
        left.number,
        left.details,
        left.costed,
        left.capture,
        left.payments,
        left.cancellation,
        left.version,
    ) == (
        right.number,
        right.details,
        right.costed,
        right.capture,
        right.payments,
        right.cancellation,
        right.version,
    )
