"""Routes des ventes (UC-VEN-01, 02, 04 à 08) — specs § 6.3 et § 6.4, sous `/shops/{shop_id}/…`.

- `GET /sales?from=&to=&seller_id=&article_id=&payment_mode_id=&kind=&q=&cursor=&limit=` :
  liste (du jour par défaut), totaux de la période ; `q` = numéro ou châssis, toutes dates.
- `POST /sales` : 201, ou 200 si l'`id` client existe déjà ; `X-Captured-At` facultatif.
- `GET/PATCH /sales/{id}` (modification : `version` + `reason`, propriétaire),
  `POST /sales/{id}/cancel {reason, refund_payments}` (propriétaire),
  `POST /sales/{id}/error-reports` (vendeur sur ses ventes ; 201, ou 200 au rejeu de l'`id`),
  `POST /error-reports/{id}/reply` (propriétaire), `GET /sales/{id}/receipt` (DTO de reçu).

Vendeur : vue sans coût ni marge (clés absentes). Comptable et chauffeur : 403 (journalisé,
RG-D03). Vente d'une autre boutique ou d'un autre vendeur : 404.
"""

from datetime import date, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Query, Response, status

from app.application.ports.pagination import MAX_LIMIT, PageRequest
from app.application.sales.search import SaleCriteria
from app.application.sales.use_cases.cancel_sale import CancelSaleCommand
from app.application.sales.use_cases.error_reports import AnswerCommand, ReportCommand
from app.application.sales.use_cases.modify_sale import ModifySaleCommand
from app.application.sales.use_cases.record_sale import RecordSaleCommand
from app.application.security.actor import Actor
from app.domain.catalog.ids import ArticleId
from app.domain.sales.ids import ErrorReportId, SaleId
from app.domain.sales.values import SaleKind
from app.domain.shared.ids import UserId
from app.domain.shops.ids import PaymentModeId
from app.interface.http.presenters.receipts import receipt_response
from app.interface.http.presenters.sales import page_response, report_response, sale_response
from app.interface.http.routes.expense_inputs import captured_at_of
from app.interface.http.routes.sales_components import SalesComponents
from app.interface.http.routes.sales_inputs import optional, sale_input_of, sale_patch_of
from app.interface.http.schemas import sales_requests as q
from app.interface.http.schemas.receipts import ReceiptResponse
from app.interface.http.schemas.sales import ErrorReportResponse, SalePageResponse, SaleResponse

IdQuery = Annotated[str | None, Query(max_length=64)]


def build_sales_router(sales: SalesComponents) -> APIRouter:
    router = APIRouter(tags=["sales"])
    Member = Annotated[Actor, Depends(sales.guard.current_actor)]  # noqa: N806
    sparse: dict[str, Any] = {"response_model_exclude_unset": True}

    @router.get("/shops/{shop_id}/sales", **sparse)
    def list_sales(
        actor: Member,
        first_day: Annotated[date | None, Query(alias="from")] = None,
        last_day: Annotated[date | None, Query(alias="to")] = None,
        seller_id: IdQuery = None,
        article_id: IdQuery = None,
        payment_mode_id: IdQuery = None,
        kind: SaleKind | None = None,
        text: Annotated[str | None, Query(alias="q", max_length=64)] = None,
        cursor: Annotated[str | None, Query(max_length=256)] = None,
        limit: Annotated[int | None, Query(ge=1, le=MAX_LIMIT)] = None,
    ) -> SalePageResponse:
        criteria = SaleCriteria(
            first_day=first_day,
            last_day=last_day,
            seller_id=optional(UserId, seller_id),
            article_id=optional(ArticleId, article_id),
            payment_mode_id=optional(PaymentModeId, payment_mode_id),
            kind=kind,
            text=text,
        )
        return page_response(sales.list.execute(actor, criteria, PageRequest.parse(cursor, limit)))

    @router.post("/shops/{shop_id}/sales", status_code=status.HTTP_201_CREATED, **sparse)
    def record_sale(
        actor: Member,
        body: q.SaleCreateRequest,
        response: Response,
        x_captured_at: Annotated[datetime | None, Header()] = None,
    ) -> SaleResponse:
        command = RecordSaleCommand(
            data=sale_input_of(body),
            sale_id=optional(SaleId, body.id),
            captured_at=captured_at_of(x_captured_at),
        )
        view, created = sales.record.execute(actor, command)
        if not created:
            response.status_code = status.HTTP_200_OK
        return sale_response(view)

    @router.get("/shops/{shop_id}/sales/{sale_id}", **sparse)
    def get_sale(actor: Member, sale_id: str) -> SaleResponse:
        return sale_response(sales.get.execute(actor, SaleId.parse(sale_id)))

    @router.patch("/shops/{shop_id}/sales/{sale_id}", **sparse)
    def modify_sale(actor: Member, sale_id: str, body: q.SalePatch) -> SaleResponse:
        command = ModifySaleCommand(
            sale_id=SaleId.parse(sale_id),
            version=body.version,
            reason=body.reason,
            patch=sale_patch_of(body),
        )
        return sale_response(sales.modify.execute(actor, command))

    @router.post("/shops/{shop_id}/sales/{sale_id}/cancel", **sparse)
    def cancel_sale(actor: Member, sale_id: str, body: q.CancelSaleRequest) -> SaleResponse:
        command = CancelSaleCommand(
            sale_id=SaleId.parse(sale_id),
            reason=body.reason,
            refund_payments=body.refund_payments,
        )
        return sale_response(sales.cancel.execute(actor, command))

    @router.post(
        "/shops/{shop_id}/sales/{sale_id}/error-reports", status_code=status.HTTP_201_CREATED
    )
    def report_error(
        actor: Member, sale_id: str, body: q.ErrorReportRequest, response: Response
    ) -> ErrorReportResponse:
        command = ReportCommand(
            sale_id=SaleId.parse(sale_id),
            description=body.description,
            report_id=optional(ErrorReportId, body.id),
        )
        report, created = sales.report.execute(actor, command)
        if not created:
            response.status_code = status.HTTP_200_OK
        return report_response(report)

    @router.post("/shops/{shop_id}/error-reports/{report_id}/reply")
    def answer_report(
        actor: Member, report_id: str, body: q.ErrorReplyRequest
    ) -> ErrorReportResponse:
        command = AnswerCommand(
            report_id=ErrorReportId.parse(report_id),
            reply=body.reply,
            handled=body.handled,
            version=body.version,
        )
        return report_response(sales.answer.execute(actor, command))

    @router.get("/shops/{shop_id}/sales/{sale_id}/receipt")
    def get_receipt(actor: Member, sale_id: str) -> ReceiptResponse:
        return receipt_response(sales.receipt.execute(actor, SaleId.parse(sale_id)))

    return router
