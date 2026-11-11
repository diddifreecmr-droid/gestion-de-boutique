"""Mise en œuvre de `Entitlements` et garde `require_entitlement` (TR-26, D17).

Décision pour `(boutique, droit)` : la surcharge de l'administrateur si elle existe, sinon
l'offre de la boutique (`PLAN_ENTITLEMENTS`). Rien n'est mis en cache : une surcharge prend
effet à la requête suivante, sans redéploiement.

Usage dans un cas d'utilisation (T23, `POST /sync`) :

    require_entitlement(entitlements, actor_shop, Entitlement.OFFLINE_CAPTURE)
"""

from app.application.plans.ports import (
    EntitlementOverride,
    EntitlementOverrides,
    Entitlements,
    ShopPlans,
)
from app.application.ports.clock import Clock
from app.application.security.actor import Actor
from app.application.security.policy import Policy
from app.domain.plans.entitlements import Entitlement, PlanCode, plan_grants
from app.domain.shared.errors import FeatureDisabled
from app.domain.shared.ids import ShopId


class FixedShopPlans(ShopPlans):
    """Toutes les boutiques sur une même offre (gratuite) — jusqu'au stockage de l'offre (T10)."""

    def __init__(self, plan: PlanCode = PlanCode.FREE) -> None:
        self._plan = PlanCode(plan)

    def plan_of(self, shop_id: ShopId) -> PlanCode:
        return self._plan


class PlanEntitlements(Entitlements):
    def __init__(self, plans: ShopPlans, overrides: EntitlementOverrides) -> None:
        self._plans = plans
        self._overrides = overrides

    def is_enabled(self, shop_id: ShopId, entitlement: Entitlement) -> bool:
        override = self._overrides.find(shop_id, entitlement)
        if override is not None:
            return override.enabled
        return plan_grants(self._plans.plan_of(shop_id), entitlement)


def require_entitlement(
    entitlements: Entitlements, shop_id: ShopId, entitlement: Entitlement
) -> None:
    """Lève `FeatureDisabled` (403 `FEATURE_DISABLED`) si le droit n'est pas ouvert."""
    if not entitlements.is_enabled(shop_id, entitlement):
        msg = "Fonction non disponible dans l'offre de la boutique"
        raise FeatureDisabled(msg, details={"entitlement": entitlement.value})


class SetEntitlementOverride:
    """Console plateforme : l'administrateur active ou désactive un droit pour une boutique."""

    def __init__(self, overrides: EntitlementOverrides, policy: Policy, clock: Clock) -> None:
        self._overrides = overrides
        self._policy = policy
        self._clock = clock

    def execute(
        self, actor: Actor, shop_id: ShopId, entitlement: Entitlement, enabled: bool | None
    ) -> None:
        """`enabled=None` retire la surcharge (retour à l'offre)."""
        self._policy.require_platform_admin(actor)
        if enabled is None:
            self._overrides.remove(shop_id, entitlement)
            return
        self._overrides.put(
            EntitlementOverride(
                shop_id=shop_id,
                entitlement=entitlement,
                enabled=enabled,
                set_by=actor.user_id,
                set_at=self._clock.now(),
            )
        )
