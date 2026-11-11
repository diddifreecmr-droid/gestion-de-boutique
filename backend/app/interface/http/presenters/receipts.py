"""Présentation du reçu (UC-VEN-04) et des clients (UC-VEN-11).

Le reçu ne lit **aucun** champ de coût de la vente : seuls nom, quantité, prix vendu et total
de ligne en sortent (SEC-N04, même pour le propriétaire).
"""

from app.application.sales.receipt import Receipt
from app.application.sales.use_cases.manage_customers import CustomerSheet
from app.domain.sales.customer import Customer
from app.interface.http.presenters.sales import detail_response, sale_response
from app.interface.http.schemas import customers as c
from app.interface.http.schemas import receipts as r


def receipt_response(receipt: Receipt) -> r.SaleReceiptResponse:
    sale, shop, settings = receipt.sale, receipt.shop.identity, receipt.settings
    customer = receipt.customer
    return r.SaleReceiptResponse(
        title=receipt.title,
        header=r.ReceiptHeader(
            shop_name=shop.name,
            city=shop.city,
            phone=shop.phone.e164,
            address=shop.address,
            niu=shop.niu,
            rccm=shop.rccm,
            show_logo=settings.show_logo,
        ),
        sale_id=str(sale.id),
        number=str(sale.number),
        provisional_number=None
        if sale.provisional_number is None
        else str(sale.provisional_number),
        sold_at=sale.sold_at,
        seller_name=receipt.seller_name,
        customer=None
        if customer is None
        else r.ReceiptCustomer(name=customer.name, phone=customer.details.phone.e164),
        lines=[
            r.ReceiptLineResponse(
                article_name=line.article_name,
                sale_mode=line.sale_mode.value,
                quantity=str(line.quantity),
                unit_price=line.unit_price,
                line_total=line.line_total,
                details=[detail_response(d) for d in line.details],
            )
            for line in receipt.lines
        ],
        total=sale.total.amount,
        paid=sale.paid.amount,
        payments=[
            r.ReceiptPaymentResponse(mode_name=p.mode_name, amount=p.amount, reference=p.reference)
            for p in receipt.payments
        ],
        remaining=sale.remaining.amount,
        mentions=[r.ReceiptMention(code=m.value, label=m.label) for m in receipt.mentions],
        footer_message=settings.footer_message,
        printing=r.ReceiptPrintSettings(
            receipt_format=settings.receipt_format.value,
            paper_width_mm=settings.paper_width_mm,
            printable_width_mm=settings.printable_width_mm,
            padding_mm=settings.margin_mm,
            font_size_pt=settings.font_size_pt,
            copies=settings.copies,
        ),
        print_sequence=receipt.print_sequence,
        printed_at=receipt.printed_at,
    )


def customer_response(customer: Customer) -> c.CustomerResponse:
    d = customer.details
    return c.CustomerResponse(
        id=str(customer.id),
        name=d.name,
        phone=d.phone.e164,
        kind=d.kind.value,
        city=d.city,
        address=d.address,
        id_doc_type=None if d.id_doc_type is None else d.id_doc_type.value,
        id_doc_number=d.id_doc_number,
        id_doc_photo_id=None if d.id_doc_photo_id is None else str(d.id_doc_photo_id),
        credit_limit=None if d.credit_limit is None else d.credit_limit.amount,
        note=d.note,
        created_by=str(customer.created_by),
        version=customer.version,
    )


def sheet_response(sheet: CustomerSheet) -> c.CustomerSheetResponse:
    return c.CustomerSheetResponse(
        customer=customer_response(sheet.customer),
        total_bought=sheet.total_bought.amount,
        total_due=sheet.total_due.amount,
        sales=[sale_response(view) for view in sheet.sales],
    )
