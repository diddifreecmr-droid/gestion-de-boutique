"""Traduction des corps de requête des ventes en saisies des cas d'utilisation (§ 6.1, § 6.4).

Identifiants : `EntityId.parse` (illisible → 400 `INVALID_IDENTIFIER`). Quantités : chaînes
décimales lues par `Decimal` (illisible → 400 `INVALID_QUANTITY`). `PATCH` : seuls les champs
présents ; `customer: null` retire le client (refusé pour une vente à crédit).
"""

from decimal import Decimal, InvalidOperation
from typing import Any

from app.application.sales.inputs import CustomerInput, LineInput, PaymentInput, SaleInput
from app.application.sales.use_cases.modify_sale import LinePatch
from app.domain.catalog.ids import ArticleId
from app.domain.sales.ids import CustomerId, PriceRequestId, SalePaymentId
from app.domain.sales.lines import SoldDetail
from app.domain.sales.values import CreditTerms
from app.domain.shared.errors import InvalidQuantity
from app.domain.shared.ids import EntityId, UserId
from app.domain.shops.ids import LocationId, PaymentModeId
from app.interface.http.schemas import sales_requests as q

CONTROL = frozenset({"version", "reason"})


def optional[IdT: EntityId](kind: type[IdT], text: str | None) -> IdT | None:
    return None if text is None else kind.parse(text)


def decimal_of(text: str) -> Decimal:
    try:
        return Decimal(text.strip())
    except InvalidOperation as exc:
        msg = "Quantité illisible"
        raise InvalidQuantity(msg, details={"field": "lines.quantity"}) from exc


def details_of(details: list[q.DetailRequest]) -> tuple[SoldDetail, ...]:
    return tuple(
        SoldDetail(
            color=d.color,
            chassis_number=d.chassis_number,
            engine_number=d.engine_number,
            size=d.size,
        )
        for d in details
    )


def payments_of(payments: list[q.SalePaymentRequest]) -> tuple[PaymentInput, ...]:
    return tuple(
        PaymentInput(
            mode_id=PaymentModeId.parse(p.mode_id),
            amount=p.amount,
            reference=p.reference,
            payment_id=optional(SalePaymentId, p.id),
        )
        for p in payments
    )


def customer_of(body: q.SaleCustomerRequest | None) -> CustomerInput | None:
    if body is None:
        return None
    return CustomerInput(
        customer_id=optional(CustomerId, body.id), name=body.name, phone=body.phone, kind=body.kind
    )


def sale_input_of(body: q.SaleCreateRequest) -> SaleInput:
    credit = body.credit
    return SaleInput(
        kind=body.kind,
        lines=tuple(
            LineInput(
                article_id=ArticleId.parse(line.article_id),
                quantity=decimal_of(line.quantity),
                unit_price=line.unit_price,
                sale_mode=line.sale_mode,
                details=details_of(line.details),
            )
            for line in body.lines
        ),
        payments=payments_of(body.payments),
        sold_on=body.sold_on,
        location_id=optional(LocationId, body.location_id),
        customer=customer_of(body.customer),
        credit=None
        if credit is None
        else CreditTerms(reminder_on=credit.reminder_on, terms=credit.terms),
        note=body.note,
        seller_id=optional(UserId, body.seller_id),
        price_request_id=optional(PriceRequestId, body.price_request_id),
    )


def sale_patch_of(body: q.SalePatch) -> dict[str, Any]:
    patch: dict[str, Any] = {}
    for name in body.model_fields_set - CONTROL:
        value = getattr(body, name)
        if name == "lines" and value is not None:
            patch[name] = tuple(
                LinePatch(
                    unit_price=line.unit_price,
                    details=None if line.details is None else details_of(line.details),
                    article_id=optional(ArticleId, line.article_id),
                    quantity=None if line.quantity is None else decimal_of(line.quantity),
                )
                for line in value
            )
        elif name == "payments" and value is not None:
            patch[name] = payments_of(value)
        elif name == "customer":
            patch[name] = customer_of(value)
        elif value is not None or name == "note":
            patch[name] = value
    return patch
