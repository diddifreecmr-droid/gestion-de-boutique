"""Actions du propriétaire : déconnexion à distance (RG-D07, SEC-R01 à R06), déblocage
(SEC-L07), code provisoire (UC-SOC-04)."""

import pytest

from app.application.identity.ports import TemporaryPinGenerator
from app.application.identity.use_cases.reset_pin import ResetPin
from app.application.identity.use_cases.revoke_user_devices import RevokeUserDevices
from app.application.identity.use_cases.unlock_user import UnlockUser
from app.application.security.actor import Actor
from app.application.security.errors import PermissionDenied, ShopAccessDenied
from app.application.security.roles import Role
from app.domain.identity.credentials import pin_weakness
from app.domain.identity.errors import AccountLocked, InvalidCredentials, SessionRevoked
from app.domain.identity.user import User, UserStatus
from app.domain.shared.errors import InvalidStateTransition, NotFound
from app.domain.shared.ids import DeviceId
from tests.application.identity.support import OTHER_SHOP, PIN, SHOP, World


def actor(user: User, role: Role) -> Actor:
    return Actor.member(user_id=user.id, device_id=DeviceId.new(), shop_id=SHOP, role=role)


def setup() -> tuple[World, User, User]:
    world = World()
    owner = world.register("670000001", role=Role.OWNER)
    seller = world.register("670000002", role=Role.SELLER)
    return world, owner, seller


def revoke(world: World) -> RevokeUserDevices:
    return RevokeUserDevices(world.uow_factory, world.access, world.clock)


def test_owner_revokes_every_device_and_the_member_can_log_in_again() -> None:
    world, owner, seller = setup()
    d1, d2 = DeviceId.new(), DeviceId.new()
    s1, s2 = world.login("670000002", device=d1), world.login("670000002", device=d2)
    assert revoke(world).execute(actor(owner, Role.OWNER), seller.id) == 2
    for issued, device in ((s1, d1), (s2, d2)):
        with pytest.raises(SessionRevoked):
            world.identity(issued, device)
    assert revoke(world).execute(actor(owner, Role.OWNER), seller.id) == 0
    assert world.login("670000002", device=d1).session_id != s1.session_id


def test_seller_cannot_revoke_devices() -> None:
    world, owner, seller = setup()
    with pytest.raises(PermissionDenied):
        revoke(world).execute(actor(seller, Role.SELLER), owner.id)


def test_member_of_another_shop_is_not_found() -> None:
    world, owner, _ = setup()
    stranger = world.register("670000003", shop=OTHER_SHOP)
    with pytest.raises(NotFound):
        revoke(world).execute(actor(owner, Role.OWNER), stranger.id)


def test_admin_without_delegation_gets_404() -> None:
    world, _, seller = setup()
    admin = Actor.platform_admin(user_id=seller.id, device_id=DeviceId.new(), shop_id=SHOP)
    with pytest.raises(ShopAccessDenied):
        revoke(world).execute(admin, seller.id)


def test_owner_unlocks_a_locked_member() -> None:
    world, owner, seller = setup()
    for _ in range(5):
        with pytest.raises(InvalidCredentials):
            world.login("670000002", "999111")
    with pytest.raises(AccountLocked):
        world.login("670000002")
    UnlockUser(world.uow_factory, world.access, world.clock).execute(
        actor(owner, Role.OWNER), seller.id
    )
    assert world.user(seller).status is UserStatus.ACTIVE
    assert world.login("670000002").access_token
    with pytest.raises(InvalidStateTransition):
        UnlockUser(world.uow_factory, world.access, world.clock).execute(
            actor(owner, Role.OWNER), seller.id
        )


class ScriptedPins(TemporaryPinGenerator):
    def __init__(self, *pins: str) -> None:
        self._pins = list(pins)

    def generate(self) -> str:
        return self._pins.pop(0)


def test_reset_gives_a_non_simple_temporary_code_to_change_at_next_login() -> None:
    world, owner, seller = setup()
    pins = ScriptedPins("123456", "000002", "531902")  # 000002 = fin du téléphone
    temporary = ResetPin(world.uow_factory, world.access, world.hasher, pins, world.clock).execute(
        actor(owner, Role.OWNER), seller.id
    )
    assert temporary == "531902"
    assert pin_weakness(temporary) is None
    with pytest.raises(InvalidCredentials):
        world.login("670000002", PIN)
    assert world.login("670000002", temporary).must_change_pin


def test_reset_fails_loudly_with_a_broken_generator() -> None:
    world, owner, seller = setup()
    pins = ScriptedPins(*(["111111"] * 32))
    use_case = ResetPin(world.uow_factory, world.access, world.hasher, pins, world.clock)
    with pytest.raises(RuntimeError, match="générateur défaillant"):
        use_case.execute(actor(owner, Role.OWNER), seller.id)
