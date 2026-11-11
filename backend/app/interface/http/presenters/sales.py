"""Présentation des ventes **selon le rôle** (TR-05, RG-D02, SEC-N01 ; specs § 6.4).

Vendeur : vue § 6.4 sans aucun coût ni marge — les quatre clés de coût d'une ligne ne sont pas
posées (`response_model_exclude_unset` les retire du JSON). Propriétaire : + `frozen_last_cost`,
`frozen_wac`, `margin`, `margin_wac` (`null` = non calculable). La décision vient de
`SaleView.show_costs` (application) ; ce module n'en prend aucune.
"""

from typing import Any

from app.application.sales.use_cases.read_sales import SaleListing
from app.application.sales.views import SaleView
from app.domain.sales.error_report import ErrorReport
from app.domain.sales.lines import SaleLine, SoldDetail
from app.domain.sales.payments import PaymentNature
from app.domain.sales.values import SaleKind, SaleStatus
from app.domain.shared.money import Money
from app.interface.http.schemas import sales as s


def _amount(value: Money | None) -> int | None:
    return None if value is None else value.amount


def detail_response(detail: SoldDetail) -> s.DetailResponse:
    return s.DetailResponse(
        color=detail.color,
        chassis_number=detail.chassis_number,
        engine_number=detail.engine_number,
        size=detail.size,
    )


def line_response(line: SaleLine, *, show_costs: bool) -> s.SaleLineResponse:
    costs: dict[str, Any] = {}
    if show_costs:
        costs = {
            "frozen_last_cost": _amount(line.frozen_last_cost),
            "frozen_wac": _amount(line.frozen_wac),
            "margin": _amount(line.margin),
            "margin_wac": _amount(line.margin_wac),
        }
    return s.SaleLineResponse(
        article_id=str(line.article_id),
        article_name=line.article_name,
        sale_mode=line.sale_mode.value,
        quantity=str(line.quantity),
        stock_quantity=str(line.stock_quantity),
        stock_unit=line.stock_quantity.unit.value,
        base_price=_amount(line.base_price),
        unit_price=line.unit_price.amount,
        line_total=line.line_total.amount,
        details=[detail_response(d) for d in line.details],
        **costs,
    )


def report_response(report: ErrorReport) -> s.ErrorReportResponse:
    return s.ErrorReportResponse(
        id=str(report.id),
        sale_id=str(report.sale_id),
        sale_number=report.sale_number,
        description=report.description,
        status=report.status.value,
        reported_by=str(report.reported_by),
        reported_at=report.reported_at,
        owner_reply=report.owner_reply,
        replied_at=report.replied_at,
        version=report.version,
    )


def sale_response(view: SaleView) -> s.SaleResponse:
    sale = view.sale
    content, capture, cancel, credit = sale.content, sale.capture, sale.cancellation, sale.credit
    nature = PaymentNature.CASH if sale.kind is SaleKind.CASH else PaymentNature.DEPOSIT
    open_credit = sale.kind is SaleKind.CREDIT and sale.status is SaleStatus.VALID
    return s.SaleResponse(
        id=str(sale.id),
        number=str(sale.number),
        provisional_number=None
        if sale.provisional_number is None
        else str(sale.provisional_number),
        status=sale.status.value,
        kind=sale.kind.value,
        sold_on=content.sold_on,
        sold_at=sale.sold_at,
        location_id=str(sale.location_id),
        seller_id=str(sale.seller_id),
        customer_id=None if content.customer_id is None else str(content.customer_id),
        total=sale.total.amount,
        paid=sale.paid.amount,
        remaining=sale.remaining.amount,
        receivable=s.ReceivableRef(id=None, remaining=sale.remaining.amount)
        if open_credit
        else None,
        lines=[line_response(line, show_costs=view.show_costs) for line in content.lines],
        payments=[
            s.SalePaymentResponse(
                id=str(p.id),
                mode_id=str(p.mode_id),
                amount=p.amount.amount,
                reference=p.reference,
                nature=nature.value,
            )
            for p in content.payments
        ],
        credit=None
        if credit is None
        else s.CreditResponse(reminder_on=credit.reminder_on, terms=credit.terms),
        note=content.note,
        stock_to_verify=sale.stock_to_verify,
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
        version=sale.version,
        warnings=[
            s.WarningResponse(code=w.code, message=w.message, details=dict(w.details))
            for w in view.warnings
        ],
        error_reports=[report_response(report) for report in view.reports],
    )


def page_response(listing: SaleListing) -> s.SalePageResponse:
    totals = listing.totals
    return s.SalePageResponse(
        items=[sale_response(view) for view in listing.items],
        next_cursor=None if listing.next_cursor is None else listing.next_cursor.encode(),
        first_day=listing.first_day,
        last_day=listing.last_day,
        totals=s.SaleTotalsResponse(
            count=totals.count, total=totals.total.amount, paid=totals.paid.amount
        ),
    )
