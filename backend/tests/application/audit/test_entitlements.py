"""Droits d'offre (TR-26) : offre gratuite → `offline_capture` faux ; surcharge de l'admin."""

from typing import Any

import pytest

from app.application.plans.entitlements import (
    FixedShopPlans,
    PlanEntitlements,
    SetEntitlementOverride,
    require_entitlement,
)
from app.application.plans.ports import EntitlementOverride
from app.application.security.actor import Actor
from app.application.security.errors import PlatformAdminRequired
from app.application.security.policy import Policy
from app.application.security.roles import Role
from app.domain.plans.entitlements import Entitlement
from app.domain.shared.errors import FeatureDisabled
from app.domain.shared.ids import DeviceId, ShopId, UserId
from app.infrastructure.persistence.memory.clock import FixedClock
from app.infrastructure.persistence.memory.entitlements import InMemoryEntitlementOverrides
from app.interface.http.errors import status_for
from tests.application.identity.support import T0

SHOP = ShopId.new()
ONE: Any = 1  # valeur d'un mauvais type, refusée à l'exécution
OFFLINE = Entitlement.OFFLINE_CAPTURE
ADMIN = Actor.platform_admin(user_id=UserId.new(), device_id=DeviceId.new())


def world() -> tuple[PlanEntitlements, SetEntitlementOverride]:
    overrides = InMemoryEntitlementOverrides()
    clock = FixedClock(T0)
    entitlements = PlanEntitlements(FixedShopPlans(), overrides)
    return entitlements, SetEntitlementOverride(overrides, Policy(clock.now), clock)


def test_free_plan_refuses_offline_capture_with_feature_disabled() -> None:
    entitlements, _ = world()
    assert entitlements.is_enabled(SHOP, OFFLINE) is False
    with pytest.raises(FeatureDisabled) as caught:
        require_entitlement(entitlements, SHOP, OFFLINE)
    assert caught.value.code == "FEATURE_DISABLED"
    assert caught.value.details == {"entitlement": "offline_capture"}
    assert status_for(caught.value) == 403


def test_admin_override_enables_then_resets_without_redeploy() -> None:
    entitlements, set_override = world()
    set_override.execute(ADMIN, SHOP, OFFLINE, True)
    require_entitlement(entitlements, SHOP, OFFLINE)  # ouvert : aucune erreur
    assert entitlements.is_enabled(ShopId.new(), OFFLINE) is False
    set_override.execute(ADMIN, SHOP, OFFLINE, False)
    assert entitlements.is_enabled(SHOP, OFFLINE) is False
    set_override.execute(ADMIN, SHOP, OFFLINE, None)
    assert entitlements.is_enabled(SHOP, OFFLINE) is False


def test_only_the_platform_admin_sets_overrides() -> None:
    _, set_override = world()
    owner = Actor.member(
        user_id=UserId.new(), device_id=DeviceId.new(), shop_id=SHOP, role=Role.OWNER
    )
    with pytest.raises(PlatformAdminRequired):
        set_override.execute(owner, SHOP, OFFLINE, True)


def test_override_values_are_checked() -> None:
    with pytest.raises(TypeError):
        EntitlementOverride(
            shop_id=SHOP, entitlement=OFFLINE, enabled=ONE, set_by=UserId.new(), set_at=T0
        )
    with pytest.raises(TypeError):
        EntitlementOverride(
            shop_id=ONE, entitlement=OFFLINE, enabled=True, set_by=UserId.new(), set_at=T0
        )
    with pytest.raises(TypeError):
        InMemoryEntitlementOverrides().put(ONE)
