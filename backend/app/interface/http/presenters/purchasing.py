"""Présentation des achats et fournisseurs (propriétaire et comptable seulement, RG-D02)."""

from app.application.ports.pagination import Cursor
from app.application.purchasing.use_cases.manage_suppliers import SupplierSheet
from app.application.purchasing.use_cases.read_purchases import PurchaseListing, PurchaseTotals
from app.application.purchasing.views import PurchaseView
from app.domain.purchasing.supplier import Supplier
from app.domain.shared.ids import EntityId
from app.interface.http.schemas import purchasing as s


def _text(value: EntityId | None) -> str | None:
    return None if value is None else str(value)


def purchase_response(view: PurchaseView) -> s.PurchaseResponse:
    purchase = view.purchase
    details, capture, cancel = purchase.details, purchase.capture, purchase.cancellation
    return s.PurchaseResponse(
        id=str(purchase.id),
        number=str(purchase.number),
        supplier_id=_text(details.supplier_id),
        purchase_date=details.purchase_date,
        location_id=str(details.location_id),
        invoice_ref=details.invoice_ref,
        invoice_photo_id=_text(details.invoice_photo_id),
        note=details.note,
        lines=[
            s.LineResponse(
                article_id=str(c.line.article_id),
                quantity=str(c.line.quantity),
                unit=c.line.unit.value,
                stock_quantity=str(c.stock_quantity),
                stock_unit=c.stock_quantity.unit.value,
                unit_price=c.line.unit_price.amount,
                total=c.total.amount,
                fee_share=c.fee_share.amount,
                final_unit_cost=c.unit_cost.amount,
            )
            for c in purchase.costed
        ],
        fees=[
            s.FeeResponse(kind=f.kind.value, label=f.label, amount=f.amount.amount)
            for f in details.fees
        ],
        article_count=len(details.lines),
        merchandise_total=purchase.merchandise_total.amount,
        fees_total=purchase.fees_total.amount,
        total=purchase.total.amount,
        paid=purchase.paid.amount,
        payment_status=purchase.payment_status.value,
        payments=[
            s.PaymentResponse(
                id=str(p.id),
                paid_on=p.paid_on,
                amount=p.amount.amount,
                mode_id=str(p.mode_id),
                reference=p.reference,
                recorded_at=p.recorded_at,
                recorded_by=str(p.recorded_by),
            )
            for p in purchase.payments
        ],
        status=purchase.status.value,
        cancellation=None
        if cancel is None
        else s.CancellationResponse(
            cancelled_at=cancel.at, cancelled_by=str(cancel.by), reason=cancel.reason
        ),
        created_by=str(capture.created_by),
        device_id=str(capture.device_id),
        captured_at=capture.captured_at,
        received_at=capture.received_at,
        editable=view.editable,
        cancellable=view.cancellable,
        last_correction_day=purchase.last_correction_day,
        version=purchase.version,
    )


def totals_response(totals: PurchaseTotals) -> s.PurchaseTotalsResponse:
    return s.PurchaseTotalsResponse(
        count=totals.count,
        merchandise=totals.merchandise.amount,
        fees=totals.fees.amount,
        total=totals.total.amount,
        paid=totals.paid.amount,
    )


def _cursor(cursor: Cursor | None) -> str | None:
    return None if cursor is None else cursor.encode()


def page_response(listing: PurchaseListing) -> s.PurchasePageResponse:
    return s.PurchasePageResponse(
        items=[purchase_response(view) for view in listing.items],
        next_cursor=_cursor(listing.next_cursor),
        first_day=listing.first_day,
        last_day=listing.last_day,
        totals=totals_response(listing.totals),
    )


def supplier_response(supplier: Supplier) -> s.SupplierResponse:
    details = supplier.details
    return s.SupplierResponse(
        id=str(supplier.id),
        name=details.name,
        phone=details.phone,
        city=details.city,
        country=details.country,
        note=details.note,
        active=details.active,
        version=supplier.version,
    )


def sheet_response(sheet: SupplierSheet) -> s.SupplierSheetResponse:
    return s.SupplierSheetResponse(
        supplier=supplier_response(sheet.supplier),
        first_day=sheet.first_day,
        last_day=sheet.last_day,
        totals=totals_response(sheet.totals),
        purchases=[purchase_response(view) for view in sheet.purchases],
    )
