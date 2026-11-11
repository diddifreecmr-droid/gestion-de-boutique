"""Actor et AdminDelegation : invariants, immuabilité, instants UTC obligatoires."""

import dataclasses
from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.application.security.actor import (
    DEFAULT_DELEGATION_DURATION,
    Actor,
    AdminDelegation,
)
from app.application.security.roles import Role
from app.domain.shared.ids import DeviceId, ShopId, UserId
from tests.application.security.support import NOW, OTHER_SHOP, SHOP, admin, member


def test_member_carries_shop_and_role() -> None:
    actor = member(Role.SELLER)
    assert actor.shop_id == SHOP
    assert actor.role is Role.SELLER
    assert actor.is_platform_admin is False
    assert actor.delegation is None


def test_actor_is_immutable() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        member(Role.SELLER).role = Role.OWNER  # type: ignore[misc]  # immuabilité prouvée


@pytest.mark.parametrize(("shop_id", "role"), [(None, Role.OWNER), (SHOP, None), (None, None)])
def test_member_requires_shop_and_role(shop_id: ShopId | None, role: Role | None) -> None:
    with pytest.raises(ValueError, match="shop_id et un Role"):
        Actor(user_id=UserId.new(), device_id=DeviceId.new(), shop_id=shop_id, role=role)


def test_member_role_must_be_a_role() -> None:
    raw_role: object = "owner"  # valeur brute : doit être refusée au profit de Role
    with pytest.raises(ValueError, match="Role"):
        Actor(user_id=UserId.new(), device_id=DeviceId.new(), shop_id=SHOP, role=raw_role)  # type: ignore[arg-type]


def test_member_cannot_carry_a_delegation() -> None:
    with pytest.raises(ValueError, match="délégation"):
        Actor(
            user_id=UserId.new(),
            device_id=DeviceId.new(),
            shop_id=SHOP,
            role=Role.OWNER,
            delegation=AdminDelegation.granted_at(SHOP, NOW),
        )


def test_platform_admin_has_no_shop_role() -> None:
    actor = admin(shop_id=None)
    assert actor.is_platform_admin is True
    assert actor.role is None
    with pytest.raises(ValueError, match="pas de rôle"):
        Actor(
            user_id=UserId.new(),
            device_id=DeviceId.new(),
            shop_id=SHOP,
            role=Role.OWNER,
            is_platform_admin=True,
        )


def test_identifiers_must_be_typed() -> None:
    wrong: object = DeviceId.new()  # identifiant d'un autre type : doit être refusé
    device = DeviceId.new()
    with pytest.raises(TypeError, match="UserId"):
        Actor.member(user_id=wrong, device_id=device, shop_id=SHOP, role=Role.OWNER)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="shop_id"):
        Actor.member(user_id=UserId.new(), device_id=device, shop_id=wrong, role=Role.OWNER)  # type: ignore[arg-type]


def test_delegation_lasts_24_hours_by_default() -> None:
    assert timedelta(hours=24) == DEFAULT_DELEGATION_DURATION
    delegation = AdminDelegation.granted_at(SHOP, NOW)
    assert delegation.expires_at == NOW + timedelta(hours=24)
    assert delegation.allows(SHOP, NOW + timedelta(hours=23, minutes=59)) is True
    assert delegation.allows(SHOP, NOW + timedelta(hours=24)) is False
    assert delegation.allows(OTHER_SHOP, NOW) is False


def test_delegation_duration_must_be_positive() -> None:
    with pytest.raises(ValueError, match="strictement positive"):
        AdminDelegation.granted_at(SHOP, NOW, timedelta(0))


@pytest.mark.parametrize(
    "moment",
    [
        datetime(2026, 11, 11, 9, 30),
        datetime(2026, 11, 11, 10, 30, tzinfo=timezone(timedelta(hours=1))),
    ],
    ids=["naif", "hors-utc"],
)
def test_delegation_requires_utc_instants(moment: datetime) -> None:
    with pytest.raises(ValueError, match="UTC"):
        AdminDelegation(SHOP, moment)
    with pytest.raises(ValueError, match="UTC"):
        AdminDelegation.granted_at(SHOP, NOW).allows(SHOP, moment)


def test_delegation_rejects_wrong_types() -> None:
    with pytest.raises(TypeError, match="ShopId"):
        AdminDelegation(UserId.new(), NOW)  # type: ignore[arg-type]  # type faux refusé
    with pytest.raises(TypeError, match="datetime"):
        AdminDelegation(SHOP, "2026-11-11T09:30:00Z")  # type: ignore[arg-type]  # type faux refusé


def test_utc_constant_is_accepted() -> None:
    assert AdminDelegation(SHOP, datetime(2026, 1, 1, tzinfo=UTC)).shop_id == SHOP
