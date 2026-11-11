"""Données de contrat des ventes : client et vente, construits par le domaine."""

from datetime import date, timedelta
from decimal import Decimal

from app.domain.audit.values import Performer
from app.domain.catalog.ids import ArticleId
from app.domain.identity.phone import PhoneNumber
from app.domain.purchasing.values import Capture
from app.domain.sales.customer import Customer, CustomerDetails, IdDocumentType
from app.domain.sales.ids import CustomerId, SaleId, SalePaymentId
from app.domain.sales.lines import SaleLine, SaleMode, SoldDetail
from app.domain.sales.payments import SalePayment
from app.domain.sales.sale import Sale
from app.domain.sales.values import CreditTerms, SaleContent, SaleKind
from app.domain.shared.doc_number import DocNumber, DocType, ProvisionalDocNumber
from app.domain.shared.ids import DeviceId, ShopId, UserId
from app.domain.shared.money import Money
from app.domain.shared.quantity import Quantity, StockUnit
from app.domain.shops.ids import LocationId, PaymentModeId
from tests.contracts.catalog_data import NOW

DEVICE = DeviceId.new()
SELLER = Performer(UserId.new(), "seller", DEVICE)
ARTICLE = ArticleId.new()


def customer(shop_id: ShopId, phone: str = "690000000", name: str = "Moussa A.") -> Customer:
    details = CustomerDetails(
        name=name,
        phone=PhoneNumber.parse(phone),
        city="Garoua",
        id_doc_type=IdDocumentType.NATIONAL_ID,
        id_doc_number="CNI-1",
        credit_limit=Money(1_000_000),
    )
    return Customer.create(shop_id, details, performer=SELLER, now=NOW)


def sale(
    shop_id: ShopId,
    sequence: int,
    *,
    chassis: str | None = "LBX123",
    customer_id: CustomerId | None = None,
    seller: UserId | None = None,
    on: date = date(2026, 11, 11),
    quantity: int = 1,
) -> Sale:
    line = SaleLine(
        article_id=ARTICLE,
        article_name="Haojue HJ125-8",
        sale_mode=SaleMode.UNIT,
        quantity=Decimal(quantity),
        stock_quantity=Quantity.of(quantity, StockUnit.UNIT),
        unit_price=Money(780_000),
        base_price=Money(780_000),
        frozen_last_cost=Money(540_000),
        details=(SoldDetail(color="Rouge", chassis_number=chassis, engine_number="M1"),),
    )
    wax = SaleLine(
        article_id=ArticleId.new(),
        article_name="Wax",
        sale_mode=SaleMode.PIECE,
        quantity=Decimal(2),
        stock_quantity=Quantity.of("11", StockUnit.METER),
        unit_price=Money(13_000),
    )
    payment = SalePayment(
        id=SalePaymentId.new(), mode_id=PaymentModeId.new(), amount=Money(300_000), reference="OM"
    )
    credit = customer_id is not None
    return Sale(
        id=SaleId.new(),
        shop_id=shop_id,
        number=DocNumber(DocType.SALE, sequence),
        kind=SaleKind.CREDIT if credit else SaleKind.CASH,
        location_id=LocationId.new(),
        seller_id=seller or SELLER.user_id,
        content=SaleContent(
            sold_on=on,
            lines=(line, wax),
            payments=(payment,) if credit else (),
            customer_id=customer_id,
            note="note",
        ),
        capture=Capture(SELLER.user_id, DEVICE, NOW, NOW + timedelta(days=(on - NOW.date()).days)),
        credit=CreditTerms(reminder_on=date(2026, 12, 1), terms="100 000 / mois")
        if credit
        else None,
        provisional_number=ProvisionalDocNumber.for_device(DocType.SALE, DEVICE, sequence),
    )


def same(left: Sale, right: Sale) -> bool:
    keys = ("number", "kind", "location_id", "seller_id", "content", "capture", "credit")
    rest = ("provisional_number", "stock_to_verify", "cancellation", "version")
    return all(getattr(left, k) == getattr(right, k) for k in keys + rest)
