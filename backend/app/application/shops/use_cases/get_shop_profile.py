"""`GET /shops/{id}/profile` : ce que le frontend construit à partir du profil (TR-15, § 4.5).

Pour **tout membre** (droit `HOME_READ`, chacun son accueil) : type et version du profil,
modules actifs, rôles proposés et leurs libellés (« Vendeur » ou « Employé »), menu **du rôle
de l'acteur** (≤ 5 entrées, sans les entrées d'un module désactivé), champs d'article et de
vente, unités, en-tête et réglages d'impression du reçu (le vendeur imprime ses reçus), prix
minimum activé, lieu habituel de l'acteur. L'administrateur sous délégation le consulte en
lecture, sans menu (il n'a pas de rôle).
"""

from dataclasses import dataclass

from app.application.ports.uow import UnitOfWorkFactory
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop
from app.application.shops.ports import (
    MembershipRepository,
    ShopRepository,
    ShopSettingsRepository,
)
from app.domain.profiles.menus import MenuEntry
from app.domain.profiles.modules import Module
from app.domain.profiles.profile import ShopProfile
from app.domain.profiles.registry import profile_for
from app.domain.shared.roles import Role
from app.domain.shops.ids import LocationId
from app.domain.shops.settings import SettingsValues
from app.domain.shops.shop import Shop


@dataclass(frozen=True, slots=True, kw_only=True)
class ShopProfileView:
    shop: Shop
    profile: ShopProfile
    settings: SettingsValues
    role: Role | None
    menu: tuple[MenuEntry, ...]
    default_location_id: LocationId | None


def visible_menu(
    entries: tuple[MenuEntry, ...], enabled: frozenset[Module]
) -> tuple[MenuEntry, ...]:
    """Menu sans les entrées des modules désactivés ; « Plus » vide disparaît."""
    visible = []
    for entry in entries:
        children = tuple(child for child in entry.children if child.module in enabled)
        if entry.module not in enabled or (entry.children and not children):
            continue
        visible.append(MenuEntry(entry.code, entry.label, entry.module, children))
    return tuple(visible)


class GetShopProfile:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy) -> None:
        self._uow_factory = uow_factory
        self._policy = policy

    def execute(self, actor: Actor) -> ShopProfileView:
        self._policy.require(actor, Permission.HOME_READ)
        with self._uow_factory(actor_shop(actor)) as uow:
            shop = ShopRepository.within(uow).current()
            settings = ShopSettingsRepository.within(uow).current()
            membership = (
                None
                if actor.is_platform_admin
                else MembershipRepository.within(uow).find_by_user(actor.user_id)
            )
        profile = profile_for(shop.profile_code)
        role = actor.role
        menu = () if role is None else visible_menu(profile.menus[role], shop.enabled_modules)
        return ShopProfileView(
            shop=shop,
            profile=profile,
            settings=settings.values,
            role=role,
            menu=menu,
            default_location_id=None if membership is None else membership.default_location_id,
        )
