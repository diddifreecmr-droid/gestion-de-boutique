"""Routes des inventaires (UC-STK-07 ; specs § 6.3) sous `/shops/{shop_id}/inventories`.

`POST` (201, ou 200 au rejeu d'un `id` connu), `GET /{id}`, `PUT /{id}/counts` (comptage
partiel, `version`), `POST /{id}/validate` (`version`, motifs), `POST /{id}/abandon`. Toutes
réservées au propriétaire et au comptable (`INVENTORY_MANAGE`).
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response, status

from app.application.security.actor import Actor
from app.domain.catalog.ids import ArticleId
from app.domain.shops.ids import LocationId
from app.domain.stock.ids import InventoryId
from app.interface.http.presenters.inventory import inventory_response
from app.interface.http.routes.stock_components import StockComponents
from app.interface.http.schemas.inventory import (
    AbandonRequest,
    CountsRequest,
    InventoryResponse,
    InventoryStartRequest,
    ValidateRequest,
)

BASE = "/shops/{shop_id}/inventories"


def build_inventories_router(stock: StockComponents) -> APIRouter:
    router = APIRouter(tags=["stock"])
    Member = Annotated[Actor, Depends(stock.guard.current_actor)]  # noqa: N806
    sparse: dict[str, Any] = {"response_model_exclude_unset": True}

    @router.post(BASE, status_code=status.HTTP_201_CREATED, **sparse)
    def start_inventory(
        actor: Member, body: InventoryStartRequest, response: Response
    ) -> InventoryResponse:
        ident = None if body.id is None else InventoryId.parse(body.id)
        location = LocationId.parse(body.location_id)
        sheet, created = stock.start_inventory.execute(actor, location, ident)
        if not created:
            response.status_code = status.HTTP_200_OK
        return inventory_response(sheet)

    @router.get(BASE + "/{inventory_id}", **sparse)
    def get_inventory(actor: Member, inventory_id: str) -> InventoryResponse:
        sheet = stock.get_inventory.execute(actor, InventoryId.parse(inventory_id))
        return inventory_response(sheet)

    @router.put(BASE + "/{inventory_id}/counts", **sparse)
    def put_counts(actor: Member, inventory_id: str, body: CountsRequest) -> InventoryResponse:
        counts = {ArticleId.parse(entry.article_id): entry.counted for entry in body.counts}
        sheet = stock.counts.execute(actor, InventoryId.parse(inventory_id), counts, body.version)
        return inventory_response(sheet)

    @router.post(BASE + "/{inventory_id}/validate", **sparse)
    def validate_inventory(
        actor: Member, inventory_id: str, body: ValidateRequest
    ) -> InventoryResponse:
        reasons = {ArticleId.parse(entry.article_id): entry.reason for entry in body.reasons}
        sheet = stock.validate_inventory.execute(
            actor,
            InventoryId.parse(inventory_id),
            body.version,
            reasons=reasons,
            global_reason=body.global_reason,
        )
        return inventory_response(sheet)

    @router.post(BASE + "/{inventory_id}/abandon", **sparse)
    def abandon_inventory(
        actor: Member, inventory_id: str, body: AbandonRequest
    ) -> InventoryResponse:
        ident = InventoryId.parse(inventory_id)
        return inventory_response(stock.abandon_inventory.execute(actor, ident, body.version))

    return router
