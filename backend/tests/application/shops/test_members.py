"""UC-SOC-04 — `ManageMembers` (MEM-01 à 04, SEC-X01, SEC-X05, SEC-X06, ERR-DUP-05)."""

import pytest

from app.application.identity.use_cases.login import CredentialKind, LoginCommand
from app.application.security.errors import PermissionDenied
from app.application.shops.use_cases.manage_members import UpdateMemberCommand
from app.domain.identity.errors import AccountDisabled
from app.domain.shared.errors import (
    Duplicate,
    InvalidStateTransition,
    NotFound,
    ValidationFailed,
    VersionConflict,
)
from app.domain.shared.ids import DeviceId, UserId
from app.domain.shared.roles import Role
from app.domain.shops.errors import LastActiveOwner, NotPointOfSale, RoleNotOffered
from tests.application.shops.support import OWNER_PHONE, World

SELLER = "677000002"


def login(world: World, phone: str, pin: str) -> None:
    world.identity.auth.login.execute(
        LoginCommand(
            phone=phone,
            secret=pin,
            kind=CredentialKind.PIN,
            device_id=DeviceId.new(),
            device_label="Android",
        )
    )


def test_seller_needs_a_point_of_sale_and_gets_a_one_time_code() -> None:
    world = World()
    owner = world.owner(world.open_motos())
    with pytest.raises(ValidationFailed) as missing:
        world.add(owner, SELLER, Role.SELLER)
    assert missing.value.details["field"] == "default_location_id"
    with pytest.raises(NotPointOfSale):
        world.add(owner, SELLER, Role.SELLER, "Ngaoundéré")
    with pytest.raises(ValidationFailed):
        world.add(owner, SELLER, Role.ACCOUNTANT, "Garoua")
    added = world.add(owner, SELLER, Role.SELLER, "Garoua")
    assert added.temporary_pin is not None
    assert added.member.must_change_pin
    assert added.member.membership.default_location_id == world.location_id(
        world.shop_of(owner), "Garoua"
    )
    login(world, SELLER, added.temporary_pin)  # le code provisoire ouvre une session


def test_existing_account_is_attached_and_double_membership_is_409() -> None:
    world = World()
    owner = world.owner(world.open_motos())
    world.add(owner, SELLER, Role.ACCOUNTANT)
    with pytest.raises(Duplicate) as caught:
        world.add(owner, SELLER, Role.ACCOUNTANT)
    assert caught.value.details["constraint"] == "membership_user"
    other = world.owner(world.open_motos(name="Motos Ngaoundéré"))
    again = world.add(other, SELLER, Role.ACCOUNTANT, name="Autre nom")
    assert again.temporary_pin is None
    assert again.member.name == "Paul"


def test_profile_roles_and_permissions() -> None:
    world = World()
    opened = world.open_motos()
    owner = world.owner(opened)
    driver = world.member(owner, "677000003", Role.DRIVER)
    with pytest.raises(PermissionDenied):
        world.http.members.list(driver)
    from app.application.shops.use_cases.open_shop import OpenShopCommand

    apparel = world.http.open_shop.execute(
        world.admin,
        OpenShopCommand(
            profile_code="apparel",
            name="Mode",
            city="Garoua",
            phone="222000000",
            owner_name="Awa",
            owner_phone="690000009",
        ),
    )
    with pytest.raises(RoleNotOffered):
        world.add(world.owner(apparel), "677000004", Role.DRIVER)


def test_role_change_and_last_owner_rule() -> None:
    world = World()
    opened = world.open_motos()
    owner = world.owner(opened)
    views = world.http.members.list(owner)
    own = views[0].membership
    demote = UpdateMemberCommand(version=own.version, role=Role.ACCOUNTANT)
    with pytest.raises(LastActiveOwner):
        world.http.members.update(owner, opened.owner_id, demote)
    with pytest.raises(LastActiveOwner):
        world.http.members.update(
            owner, opened.owner_id, UpdateMemberCommand(version=1, active=False)
        )
    second = world.add(owner, "677000005", Role.OWNER)
    assert second.member.membership.role is Role.OWNER
    changed = world.http.members.update(owner, opened.owner_id, demote)
    assert changed.membership.role is Role.ACCOUNTANT
    with pytest.raises(VersionConflict):
        world.http.members.update(owner, opened.owner_id, demote)


def test_seller_location_follows_the_role() -> None:
    world = World()
    owner = world.owner(world.open_motos())
    added = world.add(owner, SELLER, Role.SELLER, "Garoua")
    target, version = added.member.membership.user_id, added.member.membership.version
    view = world.http.members.update(
        owner, target, UpdateMemberCommand(version=version, role=Role.ACCOUNTANT)
    )
    assert view.membership.default_location_id is None
    with pytest.raises(ValidationFailed):
        world.http.members.update(
            owner, target, UpdateMemberCommand(version=view.membership.version, role=Role.SELLER)
        )
    unchanged = world.http.members.update(
        owner, target, UpdateMemberCommand(version=view.membership.version, role=Role.ACCOUNTANT)
    )
    assert unchanged.membership.version == view.membership.version
    with pytest.raises(NotFound):
        world.http.members.update(owner, UserId.new(), UpdateMemberCommand(version=1))


def test_deactivation_is_per_shop() -> None:
    """SEC-X01, X04, X06 : désactivé dans B, U garde A ; sans rattachement, plus de login."""
    world = World()
    shop_a = world.owner(world.open_motos())
    shop_b = world.owner(world.open_motos(name="Motos B", owner_phone="690000002"))
    added = world.add(shop_a, SELLER, Role.SELLER, "Garoua")
    world.add(shop_b, SELLER, Role.ACCOUNTANT)
    user = added.member.membership.user_id
    pin = added.temporary_pin
    assert pin is not None
    in_b = world.http.members.list(shop_b)[1].membership
    off = world.http.members.update(
        shop_b, user, UpdateMemberCommand(version=in_b.version, active=False)
    )
    assert not off.membership.active
    login(world, SELLER, pin)  # toujours membre actif de A
    in_a = world.http.members.list(shop_a)[1].membership
    world.http.members.update(shop_a, user, UpdateMemberCommand(version=in_a.version, active=False))
    with pytest.raises(AccountDisabled):
        login(world, SELLER, pin)
    again = world.http.members.list(shop_a)[1].membership
    world.http.members.update(shop_a, user, UpdateMemberCommand(version=again.version, active=True))
    login(world, SELLER, pin)
    entries = [e.summary for e in world.journal(world.shop_of(shop_a)) if e.module == "members"]
    assert "Compte désactivé dans la boutique" in entries


def test_owner_actions_on_the_whole_account() -> None:
    world = World()
    owner = world.owner(world.open_motos())
    added = world.add(owner, SELLER, Role.ACCOUNTANT)
    target = added.member.membership.user_id
    code = world.http.reset_pin.execute(owner, target)
    assert len(code) == 6
    assert code != added.temporary_pin
    assert world.http.revoke_devices.execute(owner, target) == 0
    with pytest.raises(InvalidStateTransition):
        world.http.unlock.execute(owner, target)
    reset = [
        e for e in world.journal(world.shop_of(owner)) if e.summary == "Code provisoire attribué"
    ]
    assert len(reset) == 1
    assert reset[0].performer.user_id == owner.user_id
    assert world.user(OWNER_PHONE).must_change_pin
