"""UC-SOC-06 — Régler la boutique (propriétaire ; recette SET-01, SET-02).

Lecture et modification des réglages (`SETTINGS_MANAGE`) et de l'en-tête du reçu (ville,
téléphone, adresse, NIU, RCCM). Modification **partielle** : seuls les champs fournis changent
(un champ facultatif envoyé à `null` est effacé), avec la `version` lue (409 sinon). Chaque
champ modifié est inscrit au journal avec son avant/après. Changer le format du reçu sans
fournir la mise en page reprend celle du profil d'impression du format (specs § 9.1). Le lieu
de réception des achats (Q-01) doit être un lieu actif de la boutique.
"""

from collections.abc import Mapping
from dataclasses import dataclass, fields, replace
from typing import Any

from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWork, UnitOfWorkFactory
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop, performer_of, require_version
from app.application.shops.ports import LocationRepository, ShopRepository, ShopSettingsRepository
from app.domain.identity.phone import PhoneNumber
from app.domain.profiles.printing import ReceiptFormat, print_profile_of
from app.domain.shared.errors import ValidationFailed
from app.domain.shops.ids import LocationId
from app.domain.shops.settings import SettingsValues
from app.domain.shops.shop import Shop

HEADER_FIELDS = frozenset({"city", "phone", "address", "niu", "rccm"})
LAYOUT_FIELDS = frozenset(
    {"paper_width_mm", "printable_width_mm", "margin_mm", "font_size_pt", "show_logo"}
)
SETTINGS_FIELDS = frozenset(item.name for item in fields(SettingsValues))


@dataclass(frozen=True, slots=True, kw_only=True)
class SettingsView:
    shop: Shop
    values: SettingsValues
    version: int


class ShopSettingsUseCase:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock

    def get(self, actor: Actor) -> SettingsView:
        self._policy.require(actor, Permission.SETTINGS_MANAGE)
        with self._uow_factory(actor_shop(actor)) as uow:
            return self._view(uow)

    def update(self, actor: Actor, patch: Mapping[str, Any], version: int) -> SettingsView:
        self._policy.require(actor, Permission.SETTINGS_MANAGE)
        unknown = set(patch) - SETTINGS_FIELDS - HEADER_FIELDS
        if unknown:
            msg = "Réglage inconnu"
            raise ValidationFailed(msg, details={"fields": sorted(unknown)})
        performer, now = performer_of(actor), self._clock.now()
        with self._uow_factory(actor_shop(actor)) as uow:
            repository = ShopSettingsRepository.within(uow)
            settings = repository.current()
            require_version(settings.version, version)
            values = self._new_values(uow, settings.values, patch)
            changed = settings.change(values, performer=performer, now=now)
            if changed:
                repository.update(settings)
            header: dict[str, Any] = {k: v for k, v in patch.items() if k in HEADER_FIELDS}
            if header:
                shops = ShopRepository.within(uow)
                shop = shops.current()
                if "phone" in header:
                    header["phone"] = PhoneNumber.parse(str(header["phone"]))
                identity = replace(shop.identity, **header)
                if shop.update_identity(identity, performer=performer, now=now):
                    shops.update(shop)
                    changed = True
            view = self._view(uow)
            if changed:
                uow.commit()
        return view

    @staticmethod
    def _new_values(
        uow: UnitOfWork, current: SettingsValues, patch: Mapping[str, Any]
    ) -> SettingsValues:
        changes: dict[str, Any] = {k: v for k, v in patch.items() if k in SETTINGS_FIELDS}
        if "receipt_format" in changes and not LAYOUT_FIELDS & set(changes):
            layout = print_profile_of(ReceiptFormat(str(changes["receipt_format"]))).layout
            changes |= {name: getattr(layout, name) for name in LAYOUT_FIELDS}
        location = changes.get("reception_location_id")
        if location is not None:
            if not isinstance(location, LocationId):
                msg = "reception_location_id doit être un LocationId"
                raise TypeError(msg)
            if not LocationRepository.within(uow).get(location).active:
                msg = "Le lieu de réception doit être un lieu actif"
                raise ValidationFailed(msg, details={"field": "reception_location_id"})
        return replace(current, **changes)

    @staticmethod
    def _view(uow: UnitOfWork) -> SettingsView:
        settings = ShopSettingsRepository.within(uow).current()
        shop = ShopRepository.within(uow).current()
        return SettingsView(shop=shop, values=settings.values, version=settings.version)
