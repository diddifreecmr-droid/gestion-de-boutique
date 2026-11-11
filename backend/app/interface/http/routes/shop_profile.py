"""`GET /shops/{id}/profile` et `GET/PATCH /shops/{id}/settings` (TR-15, UC-SOC-06)."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.application.security.actor import Actor
from app.application.shops.use_cases.shop_settings import SettingsView
from app.domain.shops.ids import LocationId
from app.interface.http.presenters.shops import profile_response, settings_response
from app.interface.http.routes.shop_components import ShopsComponents
from app.interface.http.schemas.shop import ProfileResponse, SettingsPatch, SettingsResponse


def _settings(view: SettingsView) -> SettingsResponse:
    return settings_response(view.shop, view.values, view.version)


def build_shop_profile_router(shops: ShopsComponents) -> APIRouter:
    router = APIRouter(tags=["shop"])
    Member = Annotated[Actor, Depends(shops.guard.current_actor)]  # noqa: N806

    @router.get("/shops/{shop_id}/profile")
    def profile(actor: Member) -> ProfileResponse:
        return profile_response(shops.profile.execute(actor))

    @router.get("/shops/{shop_id}/settings")
    def get_settings(actor: Member) -> SettingsResponse:
        return _settings(shops.settings.get(actor))

    @router.patch("/shops/{shop_id}/settings")
    def patch_settings(actor: Member, body: SettingsPatch) -> SettingsResponse:
        patch: dict[str, object] = {
            name: getattr(body, name) for name in body.model_fields_set if name != "version"
        }
        location = patch.get("reception_location_id")
        if isinstance(location, str):
            patch["reception_location_id"] = LocationId.parse(location)
        return _settings(shops.settings.update(actor, patch, body.version))

    return router
