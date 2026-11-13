"""Changer le type d'une boutique (console plateforme, décision client QC-1 du 2026-11-13, T27).

`POST /platform/shops/{id}/profile` — administrateur plateforme seul (403 sinon). Dans **une
seule transaction** de la boutique :

1. profil inconnu → 400 `UNKNOWN_PROFILE` ; boutique inconnue → 404 ; même profil → rien
   n'est écrit (idempotent) ;
2. la boutique doit être vide (`require_empty`) : sinon 422 `PROFILE_CHANGE_BLOCKED`,
   `details.blocking` (articles, mouvements, ventes, achats, dépenses, créances, membres d'un
   rôle absent du nouveau profil) — elle se recrée alors sur le bon profil ;
3. type et modules de départ du nouveau profil (`Shop.change_profile`, journal **sensible**),
   puis lieux, réglages, modes de paiement et catégories du profil (`profile_switch.py`).

Les modules à venir (`transfers`, `transport`, `import`) ne sont jamais activés : les profils
n'en activent aucun à l'ouverture (invariant de `ShopProfile`).
"""

from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWorkFactory
from app.application.security.actor import Actor
from app.application.security.policy import Policy
from app.application.shops.census import ShopDataCensus
from app.application.shops.context import performer_of
from app.application.shops.ports import (
    MembershipRepository,
    ShopCatalog,
    ShopRepository,
    ShopSummary,
)
from app.application.shops.profile_switch import SwitchRequest, switch_profile_content
from app.domain.profiles.registry import profile_for
from app.domain.shared.errors import NotFound
from app.domain.shared.ids import ShopId
from app.domain.shops.profile_change import locations_in_use, require_empty

SHOP_NOT_FOUND = "Boutique introuvable"


class ChangeShopProfile:
    def __init__(
        self, uow_factory: UnitOfWorkFactory, catalog: ShopCatalog, policy: Policy, clock: Clock
    ) -> None:
        self._uow_factory = uow_factory
        self._catalog = catalog
        self._policy = policy
        self._clock = clock

    def execute(self, actor: Actor, shop_id: ShopId, profile_code: str) -> ShopSummary:
        self._policy.require_platform_admin(actor)
        profile = profile_for(profile_code)
        self._summary(shop_id)  # 404 avant toute écriture
        performer, now = performer_of(actor), self._clock.now()
        with self._uow_factory(shop_id) as uow:
            shops = ShopRepository.within(uow)
            shop = shops.current()
            if shop.profile_code is not profile.code:
                members = MembershipRepository.within(uow).list_all()
                require_empty(ShopDataCensus.within(uow).counts(), members, profile)
                shop.change_profile(profile, performer=performer, now=now)
                shops.update(shop)
                request = SwitchRequest(
                    profile=profile,
                    in_use=locations_in_use(members),
                    performer=performer,
                    now=now,
                )
                switch_profile_content(uow, request)
                uow.commit()
        return self._summary(shop_id)

    def _summary(self, shop_id: ShopId) -> ShopSummary:
        summary = self._catalog.find(shop_id)
        if summary is None:
            raise NotFound(SHOP_NOT_FOUND, details={"id": str(shop_id)})
        return summary
