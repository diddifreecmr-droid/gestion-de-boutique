"""Console plateforme : droits d'offre et délégation d'une boutique (TR-23, TR-26, specs § 8.3).

Réservé à l'administrateur plateforme. La console affiche, pour une boutique :

- chaque droit d'offre, sa valeur **en vigueur** (offre du compte + surcharge) et la surcharge
  posée par l'administrateur (`None` : l'offre décide) — sans quoi l'écran ne peut pas dire ce
  qu'un `PATCH /platform/shops/{id}` va changer ;
- la fin de la délégation accordée par le propriétaire (24 h), ou `None`. L'administrateur ne
  peut **ni** l'accorder **ni** la prolonger : seul le propriétaire le fait (CDC § 4.1).

Aucune donnée métier de la boutique n'est lue ici (ni vente, ni coût, ni client).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from app.application.identity.ports import AdminDelegationDirectory
from app.application.plans.ports import EntitlementOverrides, Entitlements
from app.application.ports.clock import Clock
from app.application.security.actor import Actor
from app.application.security.policy import Policy
from app.application.shops.ports import ShopCatalog
from app.application.shops.use_cases.platform_shops import SHOP_NOT_FOUND
from app.domain.plans.entitlements import Entitlement
from app.domain.shared.errors import NotFound
from app.domain.shared.ids import ShopId


@dataclass(frozen=True, slots=True, kw_only=True)
class EntitlementState:
    entitlement: Entitlement
    enabled: bool
    """Valeur en vigueur : ce que la boutique peut faire maintenant."""
    override: bool | None
    """Surcharge de l'administrateur ; `None` si l'offre du compte décide."""


@dataclass(frozen=True, slots=True, kw_only=True)
class PlatformAccessView:
    shop_id: ShopId
    entitlements: Sequence[EntitlementState]
    admin_access_until: datetime | None


@dataclass(frozen=True, slots=True, kw_only=True)
class PlatformAccessPorts:
    """Lectures plateforme (hors de toute unité de travail de boutique)."""

    catalog: ShopCatalog
    entitlements: Entitlements
    overrides: EntitlementOverrides
    delegations: AdminDelegationDirectory


class PlatformShopAccess:
    def __init__(self, ports: PlatformAccessPorts, policy: Policy, clock: Clock) -> None:
        self._ports = ports
        self._policy = policy
        self._clock = clock

    def view(self, actor: Actor, shop_id: ShopId) -> PlatformAccessView:
        self._policy.require_platform_admin(actor)
        ports = self._ports
        if ports.catalog.find(shop_id) is None:
            raise NotFound(SHOP_NOT_FOUND, details={"id": str(shop_id)})
        states = []
        for entitlement in Entitlement:
            override = ports.overrides.find(shop_id, entitlement)
            states.append(
                EntitlementState(
                    entitlement=entitlement,
                    enabled=ports.entitlements.is_enabled(shop_id, entitlement),
                    override=None if override is None else override.enabled,
                )
            )
        until = ports.delegations.active_until(shop_id, self._clock.now())
        return PlatformAccessView(
            shop_id=shop_id, entitlements=tuple(states), admin_access_until=until
        )
