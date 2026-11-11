"""Réglages (SET-01, SET-02), profil, délégation de l'administrateur, console plateforme."""

from datetime import timedelta
from decimal import Decimal

import pytest

from app.application.identity.use_cases.authenticate import AuthenticatedUser
from app.application.security.errors import (
    PermissionDenied,
    PlatformAdminRequired,
    ShopAccessDenied,
)
from app.application.shops.use_cases.platform_shops import AdministerShopCommand
from app.domain.identity.events import SessionId
from app.domain.plans.entitlements import Entitlement, PlanCode
from app.domain.profiles.modules import Module
from app.domain.profiles.printing import ReceiptFormat
from app.domain.shared.errors import (
    InvalidStateTransition,
    NotFound,
    ValidationFailed,
    VersionConflict,
)
from app.domain.shared.ids import ShopId
from app.domain.shared.roles import Role
from app.domain.shops.errors import ModuleNotAvailable
from app.domain.shops.values import ShopStatus
from tests.application.shops.support import World


def test_settings_changes_are_journaled_and_bounded() -> None:
    world = World()
    owner = world.owner(world.open_motos())
    view = world.http.settings.get(owner)
    changed = world.http.settings.update(
        owner,
        {
            "receipt_format": ReceiptFormat.MM58,
            "copies": 2,
            "footer_message": "Merci",
            "city": "Ville",
        },
        view.version,
    )
    assert (changed.values.paper_width_mm, changed.values.copies) == (
        58,
        2,
    )  # mise en page du format
    assert changed.shop.identity.city == "Ville"
    fields = {c.field for e in world.journal(world.shop_of(owner)) for c in e.changes}
    assert {"receipt_format", "copies", "footer_message", "paper_width_mm", "city"} <= fields
    for patch in ({"copies": 0}, {"copies": 4}, {"footer_message": "x" * 201}, {"nope": 1}):
        with pytest.raises(ValidationFailed):
            world.http.settings.update(owner, patch, changed.version)
    with pytest.raises(VersionConflict):
        world.http.settings.update(owner, {"copies": 1}, 1)
    same = world.http.settings.update(owner, {"copies": 2}, changed.version)
    assert same.version == changed.version  # rien ne change, rien n'est écrit
    seller = world.member(owner, "677000002", Role.SELLER, "Garoua")
    with pytest.raises(PermissionDenied):
        world.http.settings.get(seller)


def test_reception_location_must_be_an_active_location() -> None:
    world = World()
    owner = world.owner(world.open_motos())
    shop = world.shop_of(owner)
    depot = world.location(shop, "Garoua-Boulaï")
    view = world.http.settings.update(owner, {"reception_location_id": depot.id}, 1)
    assert view.values.reception_location_id == depot.id
    world.http.locations.update(owner, world.location_id(shop, "Ngaoundéré"), {"active": False}, 1)
    with pytest.raises(ValidationFailed):
        world.http.settings.update(
            owner, {"reception_location_id": world.location_id(shop, "Ngaoundéré")}, view.version
        )
    assert world.http.settings.update(owner, {"low_stock_threshold": Decimal("2.5")}, view.version)


def test_profile_view_by_role() -> None:
    world = World()
    owner = world.owner(world.open_motos())
    seller = world.member(owner, "677000002", Role.SELLER, "Garoua")
    view = world.http.profile.execute(seller)
    assert view.profile.role_label(Role.SELLER) == "Vendeur"
    assert [entry.code for entry in view.menu] == [
        "home",
        "new_sale",
        "my_sales",
        "receivables",
        "stock",
    ]
    assert view.default_location_id == world.location_id(world.shop_of(owner), "Garoua")
    world.http.platform.administer(
        world.admin,
        world.shop_of(owner),
        AdministerShopCommand(modules=set(Module) - {Module.TRANSPORT}),
    )
    menu = world.http.profile.execute(owner).menu
    assert "trucks" not in [entry.code for entry in menu]
    assert "payroll" not in [child.code for entry in menu for child in entry.children]


def test_admin_delegation_lifecycle_and_journal() -> None:
    world = World()
    opened = world.open_motos()
    owner, shop = world.owner(opened), opened.shop_id
    authenticate = world.identity.auth.guard._authenticate
    identity = AuthenticatedUser(
        user_id=world.admin.user_id,
        session_id=SessionId.new(),
        device_id=world.admin.device_id,
        is_platform_admin=True,
        must_change_pin=False,
    )
    blind = authenticate.actor_for(identity, shop)
    with pytest.raises(ShopAccessDenied):
        world.http.locations.list(blind)
    assert world.http.grant_admin.current(owner) is None
    grant = world.http.grant_admin.execute(owner)
    assert grant.expires_at == world.clock.now() + timedelta(hours=24)
    renewed = world.http.grant_admin.execute(owner)
    assert world.http.grant_admin.current(owner).id == renewed.id  # type: ignore[union-attr]  # délégation présente
    delegated = authenticate.actor_for(identity, shop)
    assert world.http.locations.list(delegated).read_only is True
    with pytest.raises(PermissionDenied):
        world.http.grant_admin.execute(delegated)
    accesses = [e for e in world.journal(shop) if e.module == "security"]
    assert len(accesses) == 1
    assert accesses[0].sensitive
    world.http.revoke_admin.execute(owner)
    with pytest.raises(InvalidStateTransition):
        world.http.revoke_admin.execute(owner)
    world.clock.advance(timedelta(hours=25))
    assert authenticate.actor_for(identity, shop).delegation is None


def test_platform_console() -> None:
    world = World()
    opened = world.open_motos()
    shop = opened.shop_id
    [summary] = world.http.platform.list(world.admin)
    assert (summary.name, summary.plan, summary.status) == (
        "Motos Garoua",
        PlanCode.FREE,
        ShopStatus.ACTIVE,
    )
    with pytest.raises(PlatformAdminRequired):
        world.http.platform.list(world.owner(opened))
    with pytest.raises(NotFound):
        world.http.platform.get(world.admin, ShopId.new())
    command = AdministerShopCommand(
        status=ShopStatus.CLOSED, entitlements={Entitlement.OFFLINE_CAPTURE: True}
    )
    closed = world.http.platform.administer(world.admin, shop, command)
    assert closed.status is ShopStatus.CLOSED
    assert world.core.overrides.find(shop, Entitlement.OFFLINE_CAPTURE) is not None
    view = world.identity.memberships.find(opened.owner_id, shop)
    assert view is not None
    assert not view.usable
    reopened = AdministerShopCommand(
        status=ShopStatus.ACTIVE, entitlements={Entitlement.OFFLINE_CAPTURE: None}
    )
    world.http.platform.administer(world.admin, shop, reopened)
    assert world.core.overrides.find(shop, Entitlement.OFFLINE_CAPTURE) is None
    apparel_like = AdministerShopCommand(modules={Module.TRANSPORT})
    textile = _apparel(world)
    with pytest.raises(ModuleNotAvailable):
        world.http.platform.administer(world.admin, textile, apparel_like)


def _apparel(world: World) -> ShopId:
    from app.application.shops.use_cases.open_shop import OpenShopCommand

    return world.http.open_shop.execute(
        world.admin,
        OpenShopCommand(
            profile_code="textile",
            name="Pagnes",
            city="Garoua",
            phone="222000000",
            owner_name="Awa",
            owner_phone="690000009",
        ),
    ).shop_id
