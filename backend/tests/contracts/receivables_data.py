"""Données de contrat des créances : créance ancienne complète, construite par le domaine."""

from datetime import date, timedelta

from app.domain.catalog.ids import AttachmentId
from app.domain.purchasing.values import Capture
from app.domain.receivables.follow_up import Guarantor, Reminder
from app.domain.receivables.ids import GuarantorId, InstallmentId, ReceivableId, ReminderId
from app.domain.receivables.installment import Installment, InstallmentNature
from app.domain.receivables.receivable import Receivable
from app.domain.receivables.tracking import ReceivableTerms
from app.domain.sales.customer import IdDocumentType
from app.domain.sales.ids import CustomerId
from app.domain.shared.doc_number import DocNumber, DocType
from app.domain.shared.ids import ShopId, UserId
from app.domain.shared.money import Money
from app.domain.shops.ids import PaymentModeId
from tests.contracts.catalog_data import NOW
from tests.contracts.sales_data import DEVICE, SELLER

OWNER = SELLER  # l'auteur importe peu au contrat


def receivable(
    shop_id: ShopId,
    *,
    customer_id: CustomerId | None = None,
    responsible: UserId | None = None,
    opened_on: date = date(2026, 9, 1),
) -> Receivable:
    return Receivable.open_legacy(
        shop_id,
        receivable_id=ReceivableId.new(),
        customer_id=customer_id or CustomerId.new(),
        amount=Money(300_000),
        opened_on=opened_on,
        description="1 moto Haojue, cahier 2026",
        responsible_seller_id=responsible,
        terms="100 000 / mois",
        performer=OWNER,
        now=NOW,
    )


def installment(
    sequence: int, amount: int = 50_000, nature: InstallmentNature = InstallmentNature.NORMAL
) -> Installment:
    return Installment(
        id=InstallmentId.new(),
        number=DocNumber(DocType.RECEIPT, sequence),
        paid_on=date(2026, 11, 10),
        amount=Money(amount),
        mode_id=PaymentModeId.new(),
        capture=Capture(SELLER.user_id, DEVICE, NOW, NOW + timedelta(seconds=sequence)),
        reference="OM-1",
        nature=nature,
    )


def furnished(shop_id: ShopId, remind_on: date = date(2026, 12, 1)) -> Receivable:
    """Créance avec versement annulé, versement valide, rappel, garant, pièce, perte."""
    r = receivable(shop_id, responsible=SELLER.user_id)
    first, second = installment(1), installment(2, 20_000)
    r.record_installment(first, performer=OWNER)
    r.record_installment(second, performer=OWNER)
    r.cancel_installment(first.id, "erreur", performer=OWNER, now=NOW)
    reminder = Reminder(
        id=ReminderId.new(), remind_on=remind_on, created_by=SELLER.user_id, created_at=NOW
    )
    r.add_reminder(reminder, performer=OWNER)
    guarantor = Guarantor(
        id=GuarantorId.new(),
        name="Issa A.",
        phone="699112233",
        added_by=SELLER.user_id,
        added_at=NOW,
        relation="frère",
        id_doc_type=IdDocumentType.NATIONAL_ID,
        id_doc_number="CNI-2",
        id_doc_photo_id=AttachmentId.new(),
    )
    r.add_guarantor(guarantor, performer=OWNER)
    terms = ReceivableTerms(
        responsible_seller_id=SELLER.user_id, terms="x", attachment_ids=(AttachmentId.new(),)
    )
    r.change(terms, performer=OWNER, now=NOW)
    r.mark_written_off("client parti", on=date(2026, 11, 11), performer=OWNER, now=NOW)
    return r


FIELDS = (
    "customer_id",
    "origin",
    "opened_on",
    "initial_amount",
    "recorded_at",
    "sale_id",
    "sale_number",
    "sale_total",
    "paid_at_sale",
    "description",
    "responsible_seller_id",
    "terms",
    "installments",
    "reminders",
    "guarantors",
    "attachment_ids",
    "write_off",
    "sale_cancellation",
    "version",
)


def same(left: Receivable, right: Receivable) -> bool:
    return all(getattr(left, name) == getattr(right, name) for name in FIELDS)
