"""Présentation des demandes de prix et des retours **selon le rôle** (TR-05, RG-D02, SEC-N01).

Retours : coût et marges posés seulement si `SaleReturnView.show_costs` (propriétaire) ; le
vendeur voit montants, remboursement et baisse de créance de ses ventes. Demandes de prix : le
vendeur voit le minimum de ses demandes (déjà révélé par `PRICE_BELOW_MINIMUM`, Q-38).
"""

from typing import Any

from app.application.sales.return_views import SaleReturnsListing, SaleReturnView
from app.application.sales.use_cases.price_requests import PriceRequestView
from app.domain.sales.return_lines import ReturnedLine
from app.domain.shared.money import Money
from app.interface.http.presenters.sales import sale_response
from app.interface.http.schemas import sales_returns as s


def _amount(value: Money | None) -> int | None:
    return None if value is None else value.amount


def price_request_response(view: PriceRequestView) -> s.PriceRequestResponse:
    r = view.request
    return s.PriceRequestResponse(
        id=str(r.id),
        seller_id=str(r.seller_id),
        article_id=str(r.article_id),
        article_name=r.article_name,
        location_id=str(r.location_id),
        requested_price=r.requested_price.amount,
        min_price=r.min_price.amount,
        status=view.status.value,
        requested_at=r.requested_at,
        expires_at=r.expires_at,
        decided_by=None if r.decided_by is None else str(r.decided_by),
        decided_at=r.decided_at,
        sale_id=None if r.sale_id is None else str(r.sale_id),
        version=r.version,
    )


def returned_line_response(line: ReturnedLine, *, show_costs: bool) -> s.ReturnedLineResponse:
    costs: dict[str, Any] = {}
    if show_costs:
        costs = {
            "cost": _amount(line.cost),
            "margin": _amount(line.margin),
            "margin_wac": _amount(line.margin_wac),
        }
    return s.ReturnedLineResponse(
        line=line.line,
        article_id=str(line.article_id),
        article_name=line.article_name,
        quantity=str(line.quantity),
        stock_quantity=str(line.stock_quantity),
        stock_unit=line.stock_quantity.unit.value,
        condition=line.condition.value,
        amount=line.amount.amount,
        chassis=list(line.chassis),
        **costs,
    )


def return_response(view: SaleReturnView) -> s.SaleReturnResponse:
    made, refund = view.sale_return, view.sale_return.refund
    extra: dict[str, Any] = {}
    if view.show_costs:
        extra = {"margin": _amount(made.margin), "margin_wac": _amount(made.margin_wac)}
    if view.exchange is not None:
        extra["exchange_sale"] = sale_response(view.exchange)
    return s.SaleReturnResponse(
        id=str(made.id),
        sale_id=str(made.sale_id),
        sale_number=made.sale_number,
        kind=made.kind.value,
        lines=[returned_line_response(x, show_costs=view.show_costs) for x in made.lines],
        reason=made.reason,
        amount=made.amount.amount,
        refund=None
        if refund is None
        else s.RefundResponse(
            amount=refund.amount.amount,
            mode_id=str(refund.mode_id),
            refunded_on=refund.refunded_on,
        ),
        credit_reduction=made.credit_reduction.amount,
        exchange_sale_id=None if made.exchange_sale_id is None else str(made.exchange_sale_id),
        returned_at=made.returned_at,
        returned_on=made.returned_on,
        created_by=str(made.created_by),
        **extra,
    )


def returns_response(listing: SaleReturnsListing) -> s.SaleReturnsResponse:
    return s.SaleReturnsResponse(
        sale_id=str(listing.sale.id),
        returns=[return_response(view) for view in listing.returns],
        balances=[
            s.LineBalanceResponse(
                line=b.line,
                article_id=str(b.article_id),
                sold=str(b.sold),
                returned=str(b.returned),
                returnable=str(b.returnable),
            )
            for b in listing.balances
        ],
    )
