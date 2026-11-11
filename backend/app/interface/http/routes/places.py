"""`GET/POST/PATCH /shops/{id}/locations` et `/payment-modes` (UC-SOC-05, UC-SOC-06).

Création : 201, ou 200 si l'`id` fourni existe déjà (rejeu idempotent, specs § 6.1).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.application.security.actor import Actor
from app.domain.shops.ids import LocationId, PaymentModeId
from app.domain.shops.location import LocationDetails
from app.domain.shops.payment_mode import PaymentModeDetails
from app.interface.http.presenters.shops import location_response, payment_mode_response
from app.interface.http.routes.shop_components import ShopsComponents
from app.interface.http.schemas.places import (
    LocationCreateRequest,
    LocationListResponse,
    LocationPatch,
    LocationResponse,
    PaymentModeCreateRequest,
    PaymentModePatch,
    PaymentModeResponse,
)


def _patch(body: LocationPatch | PaymentModePatch) -> dict[str, object]:
    return {name: getattr(body, name) for name in body.model_fields_set if name != "version"}


def build_places_router(shops: ShopsComponents) -> APIRouter:
    router = APIRouter(tags=["shop"])
    Member = Annotated[Actor, Depends(shops.guard.current_actor)]  # noqa: N806

    @router.get("/shops/{shop_id}/locations")
    def list_locations(actor: Member) -> LocationListResponse:
        found = shops.locations.list(actor)
        return LocationListResponse(
            items=[location_response(item) for item in found.items], read_only=found.read_only
        )

    @router.post("/shops/{shop_id}/locations", status_code=status.HTTP_201_CREATED)
    def create_location(
        actor: Member, body: LocationCreateRequest, response: Response
    ) -> LocationResponse:
        details = LocationDetails(
            name=body.name,
            kind=body.kind,
            is_point_of_sale=body.is_point_of_sale,
            city=body.city,
            display_order=body.display_order,
        )
        location_id = None if body.id is None else LocationId.parse(body.id)
        location, created = shops.locations.create(actor, details, location_id)
        if not created:
            response.status_code = status.HTTP_200_OK
        return location_response(location)

    @router.patch("/shops/{shop_id}/locations/{location_id}")
    def patch_location(actor: Member, location_id: str, body: LocationPatch) -> LocationResponse:
        location = shops.locations.update(
            actor, LocationId.parse(location_id), _patch(body), body.version
        )
        return location_response(location)

    @router.get("/shops/{shop_id}/payment-modes")
    def list_payment_modes(actor: Member) -> list[PaymentModeResponse]:
        return [payment_mode_response(mode) for mode in shops.payment_modes.list(actor)]

    @router.post("/shops/{shop_id}/payment-modes", status_code=status.HTTP_201_CREATED)
    def create_payment_mode(
        actor: Member, body: PaymentModeCreateRequest, response: Response
    ) -> PaymentModeResponse:
        details = PaymentModeDetails(
            name=body.name,
            reference_required=body.reference_required,
            display_order=body.display_order,
        )
        mode_id = None if body.id is None else PaymentModeId.parse(body.id)
        mode, created = shops.payment_modes.create(actor, details, mode_id)
        if not created:
            response.status_code = status.HTTP_200_OK
        return payment_mode_response(mode)

    @router.patch("/shops/{shop_id}/payment-modes/{mode_id}")
    def patch_payment_mode(
        actor: Member, mode_id: str, body: PaymentModePatch
    ) -> PaymentModeResponse:
        mode = shops.payment_modes.update(
            actor, PaymentModeId.parse(mode_id), _patch(body), body.version
        )
        return payment_mode_response(mode)

    return router
