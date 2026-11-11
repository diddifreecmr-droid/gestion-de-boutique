"""Routes des versements et du compte client (UC-CRE-03, 05, 08) — specs § 6.3.

- `POST /receivables/{id}/installments` : versement sur cette créance (201, ou 200 au rejeu
  de l'`id`) ; `POST /customers/{id}/installments` : sur la **plus ancienne** créance du
  client ayant un reste (REC-03, choix par défaut d'UC-CRE-03) ; `X-Captured-At` facultatif.
- `POST /installments/{id}/cancel {reason}` (propriétaire), `GET /installments/{id}/receipt`
  (DTO du reçu de versement), `GET /customers/{id}/statement` (relevé, UC-CRE-05).

Vendeur : ses créances et ses clients, sinon 404. Comptable, chauffeur : 403.
"""

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Response, status

from app.application.receivables.use_cases.record_installment import (
    InstallmentCommand,
    InstallmentResult,
)
from app.application.security.actor import Actor
from app.domain.receivables.ids import InstallmentId, ReceivableId
from app.domain.sales.ids import CustomerId
from app.domain.shops.ids import PaymentModeId
from app.interface.http.presenters.receivables import (
    installment_response,
    receipt_response,
    receivable_response,
    statement_response,
)
from app.interface.http.routes.expense_inputs import captured_at_of
from app.interface.http.routes.receivables_components import ReceivablesComponents
from app.interface.http.routes.sales_inputs import optional
from app.interface.http.schemas import receivables_requests as q
from app.interface.http.schemas.receivables import (
    InstallmentReceiptResponse,
    InstallmentResultResponse,
    StatementResponse,
)


def result_response(result: InstallmentResult) -> InstallmentResultResponse:
    return InstallmentResultResponse(
        installment=installment_response(result.installment),
        receivable=receivable_response(result.view),
    )


def build_installments_router(c: ReceivablesComponents) -> APIRouter:
    router = APIRouter(tags=["receivables"])
    Member = Annotated[Actor, Depends(c.guard.current_actor)]  # noqa: N806
    sparse: dict[str, Any] = {"response_model_exclude_unset": True}

    def record(
        actor: Actor,
        body: q.InstallmentRequest,
        response: Response,
        captured: datetime | None,
        **target: Any,
    ) -> InstallmentResultResponse:
        command = InstallmentCommand(
            amount=body.amount,
            mode_id=PaymentModeId.parse(body.mode_id),
            paid_on=body.paid_on,
            reference=body.reference,
            installment_id=optional(InstallmentId, body.id),
            captured_at=captured_at_of(captured),
            **target,
        )
        result, created = c.record_installment.execute(actor, command)
        if not created:
            response.status_code = status.HTTP_200_OK
        return result_response(result)

    @router.post(
        "/shops/{shop_id}/receivables/{receivable_id}/installments",
        status_code=status.HTTP_201_CREATED,
        **sparse,
    )
    def record_on_receivable(
        actor: Member,
        receivable_id: str,
        body: q.InstallmentRequest,
        response: Response,
        x_captured_at: Annotated[datetime | None, Header()] = None,
    ) -> InstallmentResultResponse:
        target = ReceivableId.parse(receivable_id)
        return record(actor, body, response, x_captured_at, receivable_id=target)

    @router.post(
        "/shops/{shop_id}/customers/{customer_id}/installments",
        status_code=status.HTTP_201_CREATED,
        **sparse,
    )
    def record_on_customer(
        actor: Member,
        customer_id: str,
        body: q.InstallmentRequest,
        response: Response,
        x_captured_at: Annotated[datetime | None, Header()] = None,
    ) -> InstallmentResultResponse:
        target = CustomerId.parse(customer_id)
        return record(actor, body, response, x_captured_at, customer_id=target)

    @router.post("/shops/{shop_id}/installments/{installment_id}/cancel", **sparse)
    def cancel_installment(
        actor: Member, installment_id: str, body: q.ReasonRequest
    ) -> InstallmentResultResponse:
        done = c.cancel_installment.execute(
            actor, InstallmentId.parse(installment_id), body.reason or ""
        )
        return InstallmentResultResponse(
            installment=installment_response(done.installment),
            receivable=receivable_response(done.view),
        )

    @router.get("/shops/{shop_id}/installments/{installment_id}/receipt")
    def get_receipt(actor: Member, installment_id: str) -> InstallmentReceiptResponse:
        return receipt_response(c.receipt.execute(actor, InstallmentId.parse(installment_id)))

    @router.get("/shops/{shop_id}/customers/{customer_id}/statement")
    def get_statement(actor: Member, customer_id: str) -> StatementResponse:
        return statement_response(c.statement.execute(actor, CustomerId.parse(customer_id)))

    return router
