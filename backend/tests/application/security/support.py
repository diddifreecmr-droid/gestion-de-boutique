"""Fabriques partagées des tests de sécurité : acteurs, horloge figée, instant de référence."""

from datetime import UTC, datetime

from app.application.security.actor import Actor, AdminDelegation
from app.application.security.policy import Policy
from app.application.security.roles import Role
from app.domain.shared.ids import DeviceId, ShopId, UserId

NOW = datetime(2026, 11, 11, 9, 30, tzinfo=UTC)
SHOP = ShopId.new()
OTHER_SHOP = ShopId.new()


def fixed_policy(now: datetime = NOW) -> Policy:
    return Policy(clock=lambda: now)


def member(role: Role, user_id: UserId | None = None) -> Actor:
    return Actor.member(
        user_id=user_id or UserId.new(), device_id=DeviceId.new(), shop_id=SHOP, role=role
    )


def admin(delegation: AdminDelegation | None = None, shop_id: ShopId | None = SHOP) -> Actor:
    return Actor.platform_admin(
        user_id=UserId.new(), device_id=DeviceId.new(), shop_id=shop_id, delegation=delegation
    )
