"""Routes du stock (UC-STK-05, 06, 08, 10 ; specs § 6.3) sous `/shops/{shop_id}/`.

- `GET /stock?q=&location_id=&sort=name|quantity_asc|quantity_desc` : matrice (vendeur :
  quantités et prix de base seulement ; chauffeur 403).
- `GET /stock/value`, `GET /stock/damaged` : propriétaire, comptable (vendeur 403).
- `GET /articles/{id}/movements?cursor=&limit=` : historique (vendeur 403).
- `POST /adjustments` : 201, ou 200 si l'`id` fourni existe déjà (rejeu idempotent).
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response, status

from app.application.ports.pagination import PageRequest
from app.application.security.actor import Actor
from app.application.stock.use_cases.record_adjustment import AdjustmentCommand
from app.application.stock.use_cases.stock_matrix import MatrixOrder
from app.domain.catalog.ids import ArticleId, AttachmentId
from app.domain.shops.ids import LocationId
from app.domain.stock.adjustment import AdjustmentDirection, AdjustmentReason
from app.domain.stock.ids import AdjustmentId
from app.domain.stock.values import StockCondition
from app.interface.http.presenters.stock import (
    adjustment_response,
    damaged_response,
    matrix_response,
    movements_response,
    value_response,
)
from app.interface.http.routes.stock_components import StockComponents
from app.interface.http.schemas.stock import (
    AdjustmentRequest,
    AdjustmentResponse,
    DamagedStockResponse,
    MovementListResponse,
    StockMatrixResponse,
    StockValueResponse,
)


def build_stock_router(stock: StockComponents) -> APIRouter:
    router = APIRouter(tags=["stock"])
    Member = Annotated[Actor, Depends(stock.guard.current_actor)]  # noqa: N806
    sparse: dict[str, Any] = {"response_model_exclude_unset": True}

    @router.get("/shops/{shop_id}/stock", **sparse)
    def stock_matrix(
        actor: Member,
        q: Annotated[str | None, Query(max_length=100)] = None,
        location_id: Annotated[str | None, Query(max_length=64)] = None,
        sort: MatrixOrder = MatrixOrder.NAME,
    ) -> StockMatrixResponse:
        location = None if location_id is None else LocationId.parse(location_id)
        found = stock.matrix.execute(actor, text=q, location_id=location, order=sort)
        return matrix_response(found)

    @router.get("/shops/{shop_id}/stock/value")
    def stock_value(actor: Member) -> StockValueResponse:
        return value_response(stock.value.execute(actor))

    @router.get("/shops/{shop_id}/stock/damaged", **sparse)
    def damaged_stock(actor: Member) -> DamagedStockResponse:
        return damaged_response(stock.damaged.execute(actor))

    @router.get("/shops/{shop_id}/articles/{article_id}/movements", **sparse)
    def article_movements(
        actor: Member,
        article_id: str,
        cursor: Annotated[str | None, Query(max_length=512)] = None,
        limit: int | None = None,
    ) -> MovementListResponse:
        page = PageRequest.parse(cursor, limit)
        history = stock.movements.execute(actor, ArticleId.parse(article_id), page)
        return movements_response(history)

    @router.post("/shops/{shop_id}/adjustments", status_code=status.HTTP_201_CREATED)
    def record_adjustment(
        actor: Member, body: AdjustmentRequest, response: Response
    ) -> AdjustmentResponse:
        command = AdjustmentCommand(
            location_id=LocationId.parse(body.location_id),
            article_id=ArticleId.parse(body.article_id),
            direction=AdjustmentDirection(body.direction),
            quantity=body.quantity,
            condition=StockCondition(body.condition),
            reason=AdjustmentReason(body.reason),
            note=body.note,
            photo_id=None if body.photo_id is None else AttachmentId.parse(body.photo_id),
            adjustment_id=None if body.id is None else AdjustmentId.parse(body.id),
        )
        result = stock.adjust.execute(actor, command)
        if result.movement is None:
            response.status_code = status.HTTP_200_OK
        return adjustment_response(result)

    return router
