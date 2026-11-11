"""Membres (`/shops/{id}/members…`, UC-SOC-04) et délégation (`/shops/{id}/admin-access`).

`reset-pin`, `revoke-devices` et `unlock` agissent sur le **compte entier** (décision client du
11/11/2026) ; `PATCH /members/{uid}` (`active`) agit sur le rattachement à **cette** boutique.
Les codes provisoires ne sont jamais mis en cache (`Cache-Control: no-store`).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.application.security.actor import Actor
from app.application.shops.use_cases.manage_members import AddMemberCommand, UpdateMemberCommand
from app.domain.shared.ids import UserId
from app.domain.shops.ids import LocationId
from app.interface.http.presenters.shops import member_response
from app.interface.http.routes.shop_components import ShopsComponents
from app.interface.http.schemas.members import (
    AdminAccessResponse,
    MemberCreatedResponse,
    MemberCreateRequest,
    MemberPatch,
    MemberResponse,
    RevokedDevicesResponse,
    TemporaryPinResponse,
)


def _location(raw: str | None) -> LocationId | None:
    return None if raw is None else LocationId.parse(raw)


def build_members_router(shops: ShopsComponents) -> APIRouter:
    router = APIRouter(tags=["members"])
    Member = Annotated[Actor, Depends(shops.guard.current_actor)]  # noqa: N806

    @router.get("/shops/{shop_id}/members")
    def list_members(actor: Member) -> list[MemberResponse]:
        return [member_response(view) for view in shops.members.list(actor)]

    @router.post("/shops/{shop_id}/members", status_code=status.HTTP_201_CREATED)
    def add_member(
        actor: Member, body: MemberCreateRequest, response: Response
    ) -> MemberCreatedResponse:
        command = AddMemberCommand(
            name=body.name,
            phone=body.phone,
            role=body.role,
            default_location_id=_location(body.default_location_id),
        )
        added = shops.members.add(actor, command)
        response.headers["Cache-Control"] = "no-store"
        return MemberCreatedResponse(
            member=member_response(added.member),
            temporary_pin=added.temporary_pin,
            existing_account=added.temporary_pin is None,
        )

    @router.patch("/shops/{shop_id}/members/{user_id}")
    def patch_member(actor: Member, user_id: str, body: MemberPatch) -> MemberResponse:
        given = body.model_fields_set
        command = UpdateMemberCommand(
            version=body.version,
            role=body.role,
            default_location_id=_location(body.default_location_id),
            location_given="default_location_id" in given,
            active=body.active,
        )
        return member_response(shops.members.update(actor, UserId.parse(user_id), command))

    @router.post("/shops/{shop_id}/members/{user_id}/reset-pin")
    def reset_pin(actor: Member, user_id: str, response: Response) -> TemporaryPinResponse:
        temporary = shops.reset_pin.execute(actor, UserId.parse(user_id))
        response.headers["Cache-Control"] = "no-store"
        return TemporaryPinResponse(temporary_pin=temporary)

    @router.post("/shops/{shop_id}/members/{user_id}/revoke-devices")
    def revoke_devices(actor: Member, user_id: str) -> RevokedDevicesResponse:
        revoked = shops.revoke_devices.execute(actor, UserId.parse(user_id))
        return RevokedDevicesResponse(revoked_sessions=revoked)

    @router.post(
        "/shops/{shop_id}/members/{user_id}/unlock", status_code=status.HTTP_204_NO_CONTENT
    )
    def unlock(actor: Member, user_id: str) -> None:
        shops.unlock.execute(actor, UserId.parse(user_id))

    @router.get("/shops/{shop_id}/admin-access")
    def admin_access(actor: Member) -> AdminAccessResponse:
        grant = shops.grant_admin.current(actor)
        return AdminAccessResponse(
            active=grant is not None, expires_at=None if grant is None else grant.expires_at
        )

    @router.post("/shops/{shop_id}/admin-access", status_code=status.HTTP_201_CREATED)
    def grant_admin_access(actor: Member) -> AdminAccessResponse:
        grant = shops.grant_admin.execute(actor)
        return AdminAccessResponse(active=True, expires_at=grant.expires_at)

    @router.delete("/shops/{shop_id}/admin-access", status_code=status.HTTP_204_NO_CONTENT)
    def revoke_admin_access(actor: Member) -> None:
        shops.revoke_admin.execute(actor)

    return router
