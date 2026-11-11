"""Données de contrat du Tableau de bord : ventes, annulations, retour, créances, dépenses.

Journée D = 10/11/2026 (Douala). Coûts figés des motos : dernier coût 550 000, CMP 530 000.
Instants choisis pour tester la frontière UTC / Douala : 22:30Z = 23:30 le 10 (D) ;
23:00Z et 23:30Z = le 11 (D+1).
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from app.domain.catalog.ids import ArticleId
from app.domain.expenses.expense import Expense
from app.domain.purchasing.values import Capture
from app.domain.receivables.follow_up import Reminder
from app.domain.receivables.ids import InstallmentId, ReminderId
from app.domain.receivables.installment import Installment
from app.domain.receivables.receivable import Receivable
from app.domain.sales.ids import CustomerId, SaleId, SalePaymentId
from app.domain.sales.lines import SaleLine, SaleMode
from app.domain.sales.payments import SalePayment
from app.domain.sales.return_lines import AlreadyReturned, returned_line
from app.domain.sales.sale import Sale
from app.domain.sales.sale_return import Refund, SaleReturn
from app.domain.sales.values import CreditTerms, SaleContent, SaleKind
from app.domain.shared.doc_number import DocNumber, DocType
from app.domain.shared.ids import ShopId, UserId
from app.domain.shared.money import Money
from app.domain.shared.quantity import Quantity, StockUnit
from app.domain.shops.ids import LocationId, PaymentModeId
from app.domain.stock.values import StockCondition
from tests.contracts.expense_data import expense
from tests.contracts.receivables_data import receivable
from tests.contracts.sales_data import DEVICE, SELLER

D = date(2026, 11, 10)
BEFORE, AFTER = D - timedelta(days=1), D + timedelta(days=1)
CASH, MTN = PaymentModeId.new(), PaymentModeId.new()
OTHER_SELLER = UserId.new()


def at(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 11, day, hour, minute, tzinfo=UTC)


def line(price: int, *, costed: bool = True) -> SaleLine:
    return SaleLine(
        article_id=ArticleId.new(),
        article_name="Haojue HJ125-8",
        sale_mode=SaleMode.UNIT,
        quantity=Decimal(1),
        stock_quantity=Quantity.of(1, StockUnit.UNIT),
        unit_price=Money(price),
        frozen_last_cost=Money(550_000) if costed else None,
        frozen_wac=Money(530_000) if costed else None,
    )


def sale_of(
    shop_id: ShopId,
    sequence: int,
    on: date,
    lines: tuple[SaleLine, ...],
    paid: tuple[PaymentModeId, int],
    *,
    credit: bool = False,
    seller: UserId = SELLER.user_id,
) -> Sale:
    mode, amount = paid
    payment = SalePayment(id=SalePaymentId.new(), mode_id=mode, amount=Money(amount))
    instant = datetime.combine(on, datetime.min.time(), tzinfo=UTC) + timedelta(hours=9)
    return Sale(
        id=SaleId.new(),
        shop_id=shop_id,
        number=DocNumber(DocType.SALE, sequence),
        kind=SaleKind.CREDIT if credit else SaleKind.CASH,
        location_id=LocationId.new(),
        seller_id=seller,
        content=SaleContent(
            sold_on=on,
            lines=lines,
            payments=(payment,),
            customer_id=CustomerId.new() if credit else None,
        ),
        capture=Capture(seller, DEVICE, instant, instant),
        credit=CreditTerms(reminder_on=date(2026, 12, 1), terms=None) if credit else None,
    )


@dataclass(frozen=True, slots=True)
class Book:
    sales: list[Sale]
    returned: SaleReturn
    receivables: list[Receivable]


def sales_book(shop_id: ShopId) -> Book:
    s1 = sale_of(shop_id, 1, D, (line(780_000), line(100_000, costed=False)), (CASH, 880_000))
    s2 = sale_of(shop_id, 2, D, (line(700_000),), (MTN, 200_000), credit=True,
                 seller=OTHER_SELLER)  # fmt: skip
    s3 = sale_of(shop_id, 3, BEFORE, (line(790_000),), (MTN, 90_000), credit=True)
    s3.cancel("client parti", refund_payments=False, performer=SELLER, now=at(10, 22, 30))
    s4 = sale_of(shop_id, 4, D, (line(600_000),), (CASH, 600_000))
    s4.cancel("doublon", refund_payments=False, performer=SELLER, now=at(10, 23, 30))
    back = returned_line(s1.content.lines[0], 1, 1, StockCondition.SELLABLE, AlreadyReturned())
    refund = Refund(amount=Money(780_000), mode_id=CASH, refunded_on=D)
    returned = SaleReturn.record(
        s1, [back], reason="moteur", previous=[], refund=refund, performer=SELLER, now=at(10, 12)
    )
    return Book([s1, s2, s3, s4], returned, receivables_of(shop_id))


def _installment(sequence: int, amount: int) -> Installment:
    return Installment(
        id=InstallmentId.new(),
        number=DocNumber(DocType.RECEIPT, sequence),
        paid_on=D,
        amount=Money(amount),
        mode_id=CASH,
        capture=Capture(SELLER.user_id, DEVICE, at(10, 9), at(10, 9)),
    )


def _remind(r: Receivable, on: date) -> None:
    reminder = Reminder(id=ReminderId.new(), remind_on=on, created_by=SELLER.user_id,
                        created_at=at(10, 9))  # fmt: skip
    r.add_reminder(reminder, performer=SELLER)


def receivables_of(shop_id: ShopId) -> list[Receivable]:
    """Créance du vendeur (reste 250 000, rappel D), créance sans responsable (300 000, rappel
    D+5), créance passée en perte (exclue)."""
    mine = receivable(shop_id, responsible=SELLER.user_id)
    kept, voided = _installment(1, 50_000), _installment(2, 20_000)
    mine.record_installment(kept, performer=SELLER)
    mine.record_installment(voided, performer=SELLER)
    mine.cancel_installment(voided.id, "chèque", performer=SELLER, now=at(10, 23, 30))
    _remind(mine, D)
    loose = receivable(shop_id)
    _remind(loose, D + timedelta(days=5))
    lost = receivable(shop_id)
    _remind(lost, D)
    lost.mark_written_off("parti", on=D, performer=SELLER, now=at(10, 9))
    return [mine, loose, lost]


def expenses_of(shop_id: ShopId) -> list[Expense]:
    kept = expense(shop_id, 1, amount=1_000)
    voided = expense(shop_id, 2, amount=2_000)
    voided.cancel("doublon", performer=SELLER, now=at(10, 23))
    return [kept, voided]
