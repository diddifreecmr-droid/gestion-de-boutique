"""Présentation de la console plateforme : droits d'offre et délégation (aucune donnée métier)."""

from app.application.shops.use_cases.platform_access import PlatformAccessView
from app.interface.http.schemas.platform import (
    EntitlementStateResponse,
    PlatformShopAccessResponse,
)


def access_response(view: PlatformAccessView) -> PlatformShopAccessResponse:
    return PlatformShopAccessResponse(
        shop_id=str(view.shop_id),
        entitlements=[
            EntitlementStateResponse(
                code=state.entitlement, enabled=state.enabled, override=state.override
            )
            for state in view.entitlements
        ],
        admin_access_until=view.admin_access_until,
    )
