"""Routes des achats (UC-ACH-01, 03 à 06) — specs § 6.3, sous `/shops/{shop_id}/…`.

- `GET /purchases?from=&to=&supplier_id=&article_id=&location_id=&cursor=&limit=` : liste
  par date d'achat décroissante, totaux de la période (défaut : mois en cours).
- `POST /purchases` : 201, ou 200 si l'`id` client existe déjà ; `X-Captured-At` facultatif ;
  `422 PRICE_GAP_CONFIRMATION_REQUIRED` tant que `confirm_price_gap` n'est pas vrai.
- `GET/PATCH /purchases/{id}` (correction : `version` + `reason`),
  `POST /purchases/{id}/cancel {reason}` (propriétaire), `POST /purchases/{id}/payments`
  (201, ou 200 si l'`id` du paiement est déjà noté).

Vendeur et chauffeur : 403 (journalisé) ; achat d'une autre boutique : 404.
"""

from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Response, status

from app.application.ports.pagination import MAX_LIMIT, PageRequest
from app.application.purchasing.use_cases.correct_purchase import CorrectPurchaseCommand
from app.application.purchasing.use_cases.read_purchases import PurchaseCriteria
from app.application.purchasing.use_cases.record_payment import PaymentCommand
from app.application.purchasing.use_cases.record_purchase import RecordPurchaseCommand
from app.application.security.actor import Actor
from app.domain.catalog.ids import ArticleId
from app.domain.purchasing.ids import PurchaseId, SupplierId, SupplierPaymentId
from app.domain.shops.ids import LocationId, PaymentModeId
from app.interface.http.presenters.purchasing import page_response, purchase_response
from app.interface.http.routes.expense_inputs import captured_at_of
from app.interface.http.routes.purchasing_components import PurchasingComponents
from app.interface.http.routes.purchasing_inputs import input_of, optional, patch_of
from app.interface.http.schemas.purchasing import (
    PaymentRequest,
    PurchaseCancelRequest,
    PurchaseCreateRequest,
    PurchasePageResponse,
    PurchasePatch,
    PurchaseResponse,
)

IdQuery = Annotated[str | None, Query(max_length=64)]


def build_purchases_router(purchasing: PurchasingComponents) -> APIRouter:
    router = APIRouter(tags=["purchases"])
    Member = Annotated[Actor, Depends(purchasing.guard.current_actor)]  # noqa: N806

    @router.get("/shops/{shop_id}/purchases")
    def list_purchases(
        actor: Member,
        first_day: Annotated[date | None, Query(alias="from")] = None,
        last_day: Annotated[date | None, Query(alias="to")] = None,
        supplier_id: IdQuery = None,
        article_id: IdQuery = None,
        location_id: IdQuery = None,
        cursor: Annotated[str | None, Query(max_length=256)] = None,
        limit: Annotated[int | None, Query(ge=1, le=MAX_LIMIT)] = None,
    ) -> PurchasePageResponse:
        criteria = PurchaseCriteria(
            first_day=first_day,
            last_day=last_day,
            supplier_id=optional(SupplierId, supplier_id),
            article_id=optional(ArticleId, article_id),
            location_id=optional(LocationId, location_id),
        )
        listing = purchasing.list.execute(actor, criteria, PageRequest.parse(cursor, limit))
        return page_response(listing)

    @router.post("/shops/{shop_id}/purchases", status_code=status.HTTP_201_CREATED)
    def record_purchase(
        actor: Member,
        body: PurchaseCreateRequest,
        response: Response,
        x_captured_at: Annotated[datetime | None, Header()] = None,
    ) -> PurchaseResponse:
        command = RecordPurchaseCommand(
            data=input_of(body),
            purchase_id=optional(PurchaseId, body.id),
            captured_at=captured_at_of(x_captured_at),
            confirm_price_gap=body.confirm_price_gap,
        )
        view, created = purchasing.record.execute(actor, command)
        if not created:
            response.status_code = status.HTTP_200_OK
        return purchase_response(view)

    @router.get("/shops/{shop_id}/purchases/{purchase_id}")
    def get_purchase(actor: Member, purchase_id: str) -> PurchaseResponse:
        return purchase_response(purchasing.get.execute(actor, PurchaseId.parse(purchase_id)))

    @router.patch("/shops/{shop_id}/purchases/{purchase_id}")
    def correct_purchase(actor: Member, purchase_id: str, body: PurchasePatch) -> PurchaseResponse:
        command = CorrectPurchaseCommand(
            purchase_id=PurchaseId.parse(purchase_id),
            version=body.version,
            reason=body.reason,
            patch=patch_of(body),
            confirm_price_gap=body.confirm_price_gap,
        )
        return purchase_response(purchasing.correct.execute(actor, command))

    @router.post("/shops/{shop_id}/purchases/{purchase_id}/cancel")
    def cancel_purchase(
        actor: Member, purchase_id: str, body: PurchaseCancelRequest
    ) -> PurchaseResponse:
        view = purchasing.cancel.execute(actor, PurchaseId.parse(purchase_id), body.reason)
        return purchase_response(view)

    @router.post(
        "/shops/{shop_id}/purchases/{purchase_id}/payments", status_code=status.HTTP_201_CREATED
    )
    def record_payment(
        actor: Member, purchase_id: str, body: PaymentRequest, response: Response
    ) -> PurchaseResponse:
        command = PaymentCommand(
            purchase_id=PurchaseId.parse(purchase_id),
            amount=body.amount,
            mode_id=PaymentModeId.parse(body.mode_id),
            paid_on=body.paid_on,
            reference=body.reference,
            payment_id=optional(SupplierPaymentId, body.id),
        )
        view, created = purchasing.pay.execute(actor, command)
        if not created:
            response.status_code = status.HTTP_200_OK
        return purchase_response(view)

    return router
