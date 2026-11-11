"""Présentateurs du module Créances : vues de l'application → réponses HTTP (TR-05).

Les pièces d'identité des garants ne sont posées que si `show_id_docs` (propriétaire, vendeur
responsable : UC-CRE-07) ; sinon les clés sont **absentes** (`response_model_exclude_unset`).
"""

from app.application.receivables.access import ReceivableView
from app.application.receivables.use_cases.installment_receipt import InstallmentReceipt
from app.application.receivables.use_cases.read_receivables import ReceivableListing
from app.application.receivables.use_cases.statement import Statement
from app.domain.receivables.follow_up import Guarantor
from app.domain.receivables.installment import Installment
from app.domain.sales.customer import Customer
from app.interface.http.schemas import receivables as s


def customer_ref(customer: Customer) -> s.CustomerRef:
    return s.CustomerRef(id=str(customer.id), name=customer.name, phone=customer.phone_key)


def installment_response(item: Installment) -> s.InstallmentResponse:
    cancel = item.cancellation
    return s.InstallmentResponse(
        id=str(item.id),
        number=str(item.number),
        paid_on=item.paid_on,
        amount=item.amount.amount,
        mode_id=str(item.mode_id),
        reference=item.reference,
        nature=item.nature.value,
        status=item.status.value,
        to_refund=item.to_refund,
        created_by=str(item.capture.created_by),
        received_at=item.capture.received_at,
        cancelled_at=None if cancel is None else cancel.at,
        cancelled_by=None if cancel is None else str(cancel.by),
        cancel_reason=None if cancel is None else cancel.reason,
    )


def guarantor_response(item: Guarantor, *, show_id_docs: bool) -> s.GuarantorResponse:
    if not show_id_docs:
        return s.GuarantorResponse(
            id=str(item.id), name=item.name, phone=item.phone, relation=item.relation
        )
    photo = item.id_doc_photo_id
    return s.GuarantorResponse(
        id=str(item.id),
        name=item.name,
        phone=item.phone,
        relation=item.relation,
        id_doc_type=None if item.id_doc_type is None else item.id_doc_type.value,
        id_doc_number=item.id_doc_number,
        id_doc_photo_id=None if photo is None else str(photo),
    )


def receivable_response(view: ReceivableView) -> s.ReceivableResponse:
    r, off, cancel = view.receivable, view.receivable.write_off, view.receivable.sale_cancellation
    return s.ReceivableResponse(
        id=str(r.id),
        version=r.version,
        customer=customer_ref(view.customer),
        origin=r.origin.value,
        sale_id=None if r.sale_id is None else str(r.sale_id),
        sale_number=r.sale_number,
        sale_total=None if r.sale_total is None else r.sale_total.amount,
        paid_at_sale=r.paid_at_sale.amount,
        description=r.description,
        initial_amount=r.initial_amount.amount,
        total_paid=r.total_paid.amount,
        remaining=r.remaining.amount,
        status=r.status.value,
        opened_on=r.opened_on,
        seniority_days=view.seniority,
        seniority_band=view.band.value,
        last_installment_on=r.last_installment_on,
        responsible_seller_id=None
        if r.responsible_seller_id is None
        else str(r.responsible_seller_id),
        terms=r.terms,
        attachment_ids=[str(a) for a in r.attachment_ids],
        write_off=None
        if off is None
        else s.WriteOffResponse(on=off.on, reason=off.reason, by=str(off.by)),
        cancelled_on=None if cancel is None else cancel.on,
        manageable=view.manageable,
        installments=[installment_response(i) for i in r.installments],
        reminders=[
            s.ReminderResponse(
                id=str(m.id),
                remind_on=m.remind_on,
                note=m.note,
                status=m.status.value,
                alerted_for=m.alerted_for,
            )
            for m in r.reminders
        ],
        guarantors=[guarantor_response(g, show_id_docs=view.show_id_docs) for g in r.guarantors],
    )


def listing_response(listing: ReceivableListing) -> s.ReceivableListResponse:
    summary = listing.summary
    return s.ReceivableListResponse(
        summary=s.ReceivableSummaryResponse(
            total_due=summary.total_due.amount,
            debtor_count=summary.debtor_count,
            received_today=summary.received_today.amount,
        ),
        items=[receivable_response(view) for view in listing.items],
    )


def receipt_response(receipt: InstallmentReceipt) -> s.InstallmentReceiptResponse:
    item = receipt.installment
    return s.InstallmentReceiptResponse(
        shop_name=receipt.shop_name,
        shop_city=receipt.shop_city,
        shop_phone=receipt.shop_phone,
        number=str(item.number),
        paid_on=receipt.paid_on,
        customer_name=receipt.customer_name,
        customer_phone=receipt.customer_phone,
        amount=item.amount.amount,
        mode_name=receipt.mode_name,
        reference=item.reference,
        nature=item.nature.value,
        cancelled=not item.valid,
        total_paid=receipt.total_paid.amount,
        remaining=receipt.remaining.amount,
        settled=receipt.settled,
        sale_number=receipt.sale_number,
    )


def statement_response(statement: Statement) -> s.StatementResponse:
    return s.StatementResponse(
        customer=customer_ref(statement.customer),
        total_due=statement.total_due.amount,
        lines=[
            s.StatementLineResponse(
                kind=line.kind,
                on=line.on,
                receivable_id=str(line.receivable.id),
                number=line.number,
                amount=line.amount.amount,
                cancelled=line.cancelled,
                balance_after=line.balance_after.amount,
            )
            for line in statement.lines
        ],
    )
