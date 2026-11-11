"""Routes des demandes de prix (UC-VEN-03) et des retours (UC-VEN-09), sous `/shops/{shop_id}/…`.

- `POST /price-requests` (vendeur ; 201, ou 200 au rejeu de l'`id`), `GET /price-requests`
  (vendeur : les siennes ; propriétaire : en attente), `GET /price-requests/{id}`,
  `POST /price-requests/{id}/decision {decision: accept|refuse, version?}` (propriétaire).
- `POST /sales/{id}/returns` (propriétaire ; retour simple ou `exchange` ; 201, ou 200 au
  rejeu de l'`id`), `GET /sales/{id}/returns` : retours de la vente et quantités encore
  rendables par ligne (vendeur : ses ventes, sans coût ni marge).

Comptable et chauffeur : 403 (RG-D03). Ressource d'un autre vendeur ou d'une autre boutique : 404.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response, status

from app.application.sales import returning as rt
from app.application.sales.use_cases.price_requests import PriceRequestCommand
from app.application.sales.use_cases.record_return import ExchangeInput, ReturnCommand
from app.application.security.actor import Actor
from app.domain.catalog.ids import ArticleId
from app.domain.sales.ids import PriceRequestId, SaleId, SaleReturnId
from app.domain.shops.ids import PaymentModeId
from app.interface.http.presenters.sales_returns import (
    price_request_response,
    return_response,
    returns_response,
)
from app.interface.http.routes.sales_components import SalesComponents
from app.interface.http.routes.sales_inputs import decimal_of, optional, sale_input_of
from app.interface.http.schemas import sales_returns as q


def return_command_of(sale_id: str, body: q.SaleReturnCreate) -> ReturnCommand:
    refund, exchange = body.refund, body.exchange
    return ReturnCommand(
        sale_id=SaleId.parse(sale_id),
        lines=tuple(
            rt.ReturnLineInput(
                line=line.line,
                quantity=decimal_of(line.quantity),
                condition=line.condition,
                chassis=tuple(line.chassis),
            )
            for line in body.lines
        ),
        reason=body.reason,
        refund=None
        if refund is None
        else rt.RefundInput(
            amount=refund.amount,
            mode_id=PaymentModeId.parse(refund.mode_id),
            refunded_on=refund.refunded_on,
        ),
        exchange=None
        if exchange is None
        else ExchangeInput(
            sale=sale_input_of(exchange.sale),
            mode_id=PaymentModeId.parse(exchange.mode_id),
            sale_id=optional(SaleId, exchange.sale.id),
        ),
        return_id=optional(SaleReturnId, body.id),
    )


def build_sales_returns_router(sales: SalesComponents) -> APIRouter:
    router = APIRouter(tags=["sales"])
    Member = Annotated[Actor, Depends(sales.guard.current_actor)]  # noqa: N806
    sparse: dict[str, Any] = {"response_model_exclude_unset": True}

    @router.post("/shops/{shop_id}/price-requests", status_code=status.HTTP_201_CREATED)
    def request_price(
        actor: Member, body: q.PriceRequestCreate, response: Response
    ) -> q.PriceRequestResponse:
        command = PriceRequestCommand(
            article_id=ArticleId.parse(body.article_id),
            requested_price=body.requested_price,
            sale_mode=body.sale_mode,
            request_id=optional(PriceRequestId, body.id),
        )
        view, created = sales.request_price.execute(actor, command)
        if not created:
            response.status_code = status.HTTP_200_OK
        return price_request_response(view)

    @router.get("/shops/{shop_id}/price-requests")
    def list_price_requests(actor: Member) -> list[q.PriceRequestResponse]:
        return [price_request_response(v) for v in sales.list_price_requests.execute(actor)]

    @router.get("/shops/{shop_id}/price-requests/{request_id}")
    def get_price_request(actor: Member, request_id: str) -> q.PriceRequestResponse:
        view = sales.get_price_request.execute(actor, PriceRequestId.parse(request_id))
        return price_request_response(view)

    @router.post("/shops/{shop_id}/price-requests/{request_id}/decision")
    def decide_price_request(
        actor: Member, request_id: str, body: q.PriceDecisionRequest
    ) -> q.PriceRequestResponse:
        view = sales.decide_price.execute(
            actor,
            PriceRequestId.parse(request_id),
            accept=body.decision == "accept",
            version=body.version,
        )
        return price_request_response(view)

    @router.post(
        "/shops/{shop_id}/sales/{sale_id}/returns",
        status_code=status.HTTP_201_CREATED,
        **sparse,
    )
    def record_return(
        actor: Member, sale_id: str, body: q.SaleReturnCreate, response: Response
    ) -> q.SaleReturnResponse:
        view, created = sales.record_return.execute(actor, return_command_of(sale_id, body))
        if not created:
            response.status_code = status.HTTP_200_OK
        return return_response(view)

    @router.get("/shops/{shop_id}/sales/{sale_id}/returns", **sparse)
    def list_returns(actor: Member, sale_id: str) -> q.SaleReturnsResponse:
        return returns_response(sales.list_returns.execute(actor, SaleId.parse(sale_id)))

    return router
