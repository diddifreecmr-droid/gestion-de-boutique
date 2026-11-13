"""Console plateforme : `POST/GET /platform/shops`, `GET/PATCH /platform/shops/{id}` (TR-23),
`GET /platform/shops/{id}/access` (droits d'offre en vigueur, délégation du propriétaire),
`POST /platform/shops/{id}/profile` (changer le type d'une boutique vide, QC-1, T27).

Administrateur plateforme seulement (`current_platform_actor` : un membre reçoit 403). Ouvrir
une boutique renvoie le code provisoire du propriétaire créé, **une seule fois** (PLT-01).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.application.security.actor import Actor
from app.application.shops.use_cases.open_shop import OpenShopCommand
from app.application.shops.use_cases.platform_shops import AdministerShopCommand
from app.domain.shared.ids import ShopId
from app.interface.http.presenters.platform import access_response
from app.interface.http.presenters.shops import summary_response
from app.interface.http.routes.shop_components import ShopsComponents
from app.interface.http.schemas.platform import (
    AdministerShopRequest,
    ChangeProfileRequest,
    OpenedShopResponse,
    OpenShopRequest,
    PlatformShopAccessResponse,
    ShopSummaryResponse,
)


def build_platform_router(shops: ShopsComponents) -> APIRouter:
    router = APIRouter(tags=["platform"])
    Admin = Annotated[Actor, Depends(shops.guard.current_platform_actor)]  # noqa: N806

    @router.post("/platform/shops", status_code=status.HTTP_201_CREATED)
    def open_shop(actor: Admin, body: OpenShopRequest, response: Response) -> OpenedShopResponse:
        opened = shops.open_shop.execute(
            actor,
            OpenShopCommand(
                profile_code=body.profile_code,
                name=body.name,
                city=body.city,
                phone=body.phone,
                address=body.address,
                niu=body.niu,
                rccm=body.rccm,
                owner_name=body.owner.name,
                owner_phone=body.owner.phone,
                account_name=body.account_name,
            ),
        )
        response.headers["Cache-Control"] = "no-store"  # code provisoire dans le corps
        return OpenedShopResponse(
            shop=summary_response(shops.platform.get(actor, opened.shop_id)),
            owner_id=str(opened.owner_id),
            owner_created=opened.owner_created,
            temporary_pin=opened.temporary_pin,
        )

    @router.get("/platform/shops")
    def list_shops(actor: Admin) -> list[ShopSummaryResponse]:
        return [summary_response(summary) for summary in shops.platform.list(actor)]

    @router.get("/platform/shops/{shop_id}")
    def get_shop(actor: Admin, shop_id: str) -> ShopSummaryResponse:
        return summary_response(shops.platform.get(actor, ShopId.parse(shop_id)))

    @router.patch("/platform/shops/{shop_id}")
    def administer_shop(
        actor: Admin, shop_id: str, body: AdministerShopRequest
    ) -> ShopSummaryResponse:
        command = AdministerShopCommand(
            modules=body.modules, status=body.status, entitlements=body.entitlements
        )
        return summary_response(shops.platform.administer(actor, ShopId.parse(shop_id), command))

    @router.post("/platform/shops/{shop_id}/profile")
    def change_profile(
        actor: Admin, shop_id: str, body: ChangeProfileRequest
    ) -> ShopSummaryResponse:
        """Changer le type d'une boutique **vide** (QC-1) ; sinon 422 PROFILE_CHANGE_BLOCKED."""
        changed = shops.change_profile.execute(actor, ShopId.parse(shop_id), body.profile_code)
        return summary_response(changed)

    @router.get("/platform/shops/{shop_id}/access")
    def shop_access(actor: Admin, shop_id: str) -> PlatformShopAccessResponse:
        return access_response(shops.platform_access.view(actor, ShopId.parse(shop_id)))

    return router
