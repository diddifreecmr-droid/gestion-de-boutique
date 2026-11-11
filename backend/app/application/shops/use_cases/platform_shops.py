"""Console plateforme (TR-23, UC-SOC-01) : lister les boutiques, régler modules, statut, droits.

Réservé à l'administrateur plateforme (`Policy.require_platform_admin`). Aucune donnée métier
d'une boutique n'est lue ici : seulement ce que la console affiche (nom, type, ville, statut,
modules, compte, offre). Modules : ceux du profil, socle et journal toujours actifs
(`MODULE_NOT_AVAILABLE` sinon). Droits d'offre : surcharge par boutique (`offline_capture`,
recette ERR-FEA-04) — `None` retire la surcharge, l'offre du compte décide de nouveau.
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

from app.application.plans.ports import EntitlementOverride, EntitlementOverrides
from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWorkFactory
from app.application.security.actor import Actor
from app.application.security.policy import Policy
from app.application.shops.context import performer_of
from app.application.shops.ports import ShopCatalog, ShopRepository, ShopSummary
from app.domain.plans.entitlements import Entitlement
from app.domain.profiles.modules import Module
from app.domain.profiles.registry import profile_for
from app.domain.shared.errors import NotFound
from app.domain.shared.ids import ShopId
from app.domain.shops.values import ShopStatus

SHOP_NOT_FOUND = "Boutique introuvable"


@dataclass(frozen=True, slots=True, kw_only=True)
class AdministerShopCommand:
    modules: Iterable[Module] | None = None
    status: ShopStatus | None = None
    entitlements: Mapping[Entitlement, bool | None] = field(default_factory=dict)


class PlatformShops:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        catalog: ShopCatalog,
        overrides: EntitlementOverrides,
        policy: Policy,
        clock: Clock,
    ) -> None:
        self._uow_factory = uow_factory
        self._catalog = catalog
        self._overrides = overrides
        self._policy = policy
        self._clock = clock

    def list(self, actor: Actor) -> Sequence[ShopSummary]:
        self._policy.require_platform_admin(actor)
        return self._catalog.list_all()

    def get(self, actor: Actor, shop_id: ShopId) -> ShopSummary:
        self._policy.require_platform_admin(actor)
        summary = self._catalog.find(shop_id)
        if summary is None:
            raise NotFound(SHOP_NOT_FOUND, details={"id": str(shop_id)})
        return summary

    def administer(
        self, actor: Actor, shop_id: ShopId, command: AdministerShopCommand
    ) -> ShopSummary:
        """Modules et statut (journalisés dans la boutique), puis surcharges de droits."""
        self._policy.require_platform_admin(actor)
        self.get(actor, shop_id)
        now = self._clock.now()
        if command.modules is not None or command.status is not None:
            with self._uow_factory(shop_id) as uow:
                shops = ShopRepository.within(uow)
                shop = shops.current()
                changed = shop.administer(
                    modules=command.modules,
                    status=command.status,
                    available=profile_for(shop.profile_code).available_modules,
                    performer=performer_of(actor),
                    now=now,
                )
                if changed:
                    shops.update(shop)
                    uow.commit()
        for entitlement, enabled in command.entitlements.items():
            if enabled is None:
                self._overrides.remove(shop_id, entitlement)
                continue
            self._overrides.put(
                EntitlementOverride(
                    shop_id=shop_id,
                    entitlement=Entitlement(entitlement),
                    enabled=enabled,
                    set_by=actor.user_id,
                    set_at=now,
                )
            )
        return self.get(actor, shop_id)
