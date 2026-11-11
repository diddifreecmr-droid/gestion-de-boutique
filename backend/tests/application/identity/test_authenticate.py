"""Identité de requête et `Actor` relu à chaque requête (§ 8.1, AUTH-02, SEC-R02, SEC-X02)."""

from datetime import timedelta

import pytest

from app.application.identity.use_cases.get_me import GetMe
from app.application.identity.use_cases.login import CredentialKind
from app.application.security.roles import Role
from app.domain.identity.errors import (
    AccountDisabled,
    PinChangeRequired,
    SessionRevoked,
    Unauthenticated,
)
from app.domain.shared.errors import NotFound
from app.domain.shared.ids import DeviceId, ShopId, UserId
from tests.application.identity.support import OTHER_SHOP, PASSWORD, SHOP, T0, World


def test_actor_role_comes_from_the_membership_at_each_request() -> None:
    world = World()
    user = world.register(role=Role.SELLER)
    device = DeviceId.new()
    identity = world.identity(world.login(device=device), device)
    assert world.authenticate.actor_for(identity, SHOP).role is Role.SELLER
    world.memberships.set_active(user.id, SHOP, active=False)
    with pytest.raises(NotFound):
        world.authenticate.actor_for(identity, SHOP)
    with pytest.raises(NotFound):
        world.authenticate.actor_for(identity, OTHER_SHOP)


def test_temporary_code_blocks_shop_routes_but_not_identity() -> None:
    world = World()
    world.register(must_change=True)
    device = DeviceId.new()
    identity = world.identity(world.login(device=device), device)
    assert identity.must_change_pin
    with pytest.raises(PinChangeRequired):
        world.authenticate.actor_for(identity, SHOP)


def test_platform_admin_actor_has_no_role_and_no_delegation() -> None:
    world = World()
    world.register("691234567", PASSWORD, admin=True)
    device = DeviceId.new()
    issued = world.login("691234567", PASSWORD, device=device, kind=CredentialKind.PASSWORD)
    actor = world.authenticate.actor_for(world.identity(issued, device), SHOP)
    assert (actor.is_platform_admin, actor.role, actor.delegation) == (True, None, None)


def test_token_is_bound_to_its_device() -> None:
    world = World()
    world.register()
    issued = world.login(device=DeviceId.new())
    with pytest.raises(Unauthenticated) as caught:
        world.identity(issued, DeviceId.new())
    assert caught.value.code == "UNAUTHENTICATED"


def test_expired_access_token_is_refused() -> None:
    world = World()
    world.register()
    device = DeviceId.new()
    issued = world.login(device=device)
    world.clock.advance(timedelta(minutes=15))
    with pytest.raises(Unauthenticated, match="expiré"):
        world.identity(issued, device)


def test_session_of_a_deleted_or_foreign_user_is_revoked() -> None:
    world = World()
    world.register()
    device = DeviceId.new()
    issued = world.login(device=device)
    claims = world.tokens.verify(issued.access_token)
    forged = world.tokens.issue(
        type(claims)(
            user_id=UserId.new(),
            session_id=claims.session_id,
            is_platform_admin=False,
            issued_at=T0,
            expires_at=T0 + timedelta(minutes=5),
        )
    )
    with pytest.raises(SessionRevoked):
        world.authenticate.identify(forged, device)


def test_disabled_user_is_refused_on_every_request() -> None:
    world = World()
    user = world.register()
    device = DeviceId.new()
    issued = world.login(device=device)
    stored = world.user(user)
    stored.disable(T0, by=UserId.new())
    world.save(stored)
    with pytest.raises(AccountDisabled):
        world.identity(issued, device)


def test_get_me_lists_active_shops_sorted_by_name() -> None:
    world = World()
    user = world.register(must_change=True)
    third = ShopId.new()
    world.memberships.grant(user.id, OTHER_SHOP, "Boutique Tissus", Role.ACCOUNTANT)
    world.memberships.grant(user.id, third, "Zz fermée", Role.OWNER)
    world.memberships.set_active(user.id, third, active=False)
    device = DeviceId.new()
    view = GetMe(world.uow_factory, world.memberships).execute(
        world.identity(world.login(device=device), device)
    )
    assert view.phone == "+237677001122"
    assert view.must_change_pin
    assert [(m.shop_name, m.role) for m in view.shops] == [
        ("Boutique Tissus", Role.ACCOUNTANT),
        ("Motos Garoua", Role.SELLER),
    ]
