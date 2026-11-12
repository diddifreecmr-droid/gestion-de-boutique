"""Console plateforme : droits d'offre en vigueur et délégation d'une boutique (TR-23, TR-26)."""

from datetime import timedelta

import pytest

from app.application.security.errors import PlatformAdminRequired
from app.application.shops.use_cases.platform_shops import AdministerShopCommand
from app.domain.plans.entitlements import Entitlement
from app.domain.shared.errors import NotFound
from app.domain.shared.ids import ShopId
from tests.application.shops.support import World


def _offline(world: World, shop: ShopId) -> tuple[bool, bool | None]:
    view = world.http.platform_access.view(world.admin, shop)
    [state] = [s for s in view.entitlements if s.entitlement is Entitlement.OFFLINE_CAPTURE]
    return state.enabled, state.override


def test_entitlements_follow_the_plan_then_the_override() -> None:
    world = World()
    shop = world.open_motos().shop_id
    assert _offline(world, shop) == (False, None)  # offre gratuite : aucun droit premium
    on = AdministerShopCommand(entitlements={Entitlement.OFFLINE_CAPTURE: True})
    world.http.platform.administer(world.admin, shop, on)
    assert _offline(world, shop) == (True, True)
    cleared = AdministerShopCommand(entitlements={Entitlement.OFFLINE_CAPTURE: None})
    world.http.platform.administer(world.admin, shop, cleared)
    assert _offline(world, shop) == (False, None)  # l'offre décide de nouveau


def test_delegation_end_is_shown_only_while_it_runs() -> None:
    world = World()
    opened = world.open_motos()
    owner = world.owner(opened)
    access = world.http.platform_access
    assert access.view(world.admin, opened.shop_id).admin_access_until is None
    grant = world.http.grant_admin.execute(owner)
    assert access.view(world.admin, opened.shop_id).admin_access_until == grant.expires_at
    world.clock.advance(timedelta(hours=24, seconds=1))
    assert access.view(world.admin, opened.shop_id).admin_access_until is None


def test_reserved_to_the_platform_admin_and_unknown_shop_is_not_found() -> None:
    world = World()
    opened = world.open_motos()
    with pytest.raises(PlatformAdminRequired):
        world.http.platform_access.view(world.owner(opened), opened.shop_id)
    with pytest.raises(NotFound):
        world.http.platform_access.view(world.admin, ShopId.new())
