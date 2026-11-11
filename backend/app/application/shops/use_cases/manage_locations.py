"""UC-SOC-05 — Gérer les lieux (propriétaire ; le comptable les voit en lecture, CDC § 4.2).

Recette LOC-01 à LOC-03. Créer (nom unique sans casse → 409 `DUPLICATE`), renommer, changer
le type, le point de vente, la ville, l'ordre d'affichage, désactiver ou réactiver. Retirer un
lieu de la vente ou le désactiver est refusé :

- s'il est le **dernier point de vente actif** → `LAST_POINT_OF_SALE` ;
- s'il est le lieu habituel d'un vendeur actif → `LOCATION_IN_USE` (`usage = default_location`) ;
- (désactivation) s'il a du stock → `LOCATION_HAS_STOCK` (port `LocationStock`, T14) ;
- (désactivation) s'il est le lieu de réception des achats → `LOCATION_IN_USE`.

Ces contrôles regardent les autres lieux : la boutique est réécrite (version incrémentée) pour
que deux retraits concurrents des deux derniers points de vente ne passent pas tous les deux.
Création idempotente : un `location_id` déjà connu renvoie le lieu existant (`created=False`).
"""

from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any

from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWork, UnitOfWorkFactory
from app.application.security.access import Access
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop, performer_of, require_version
from app.application.shops.ports import (
    LocationRepository,
    MembershipRepository,
    ShopRepository,
    ShopSettingsRepository,
)
from app.application.shops.stock_probe import LocationStock
from app.domain.shops.errors import LastPointOfSale, LocationHasStock, LocationInUse
from app.domain.shops.ids import LocationId
from app.domain.shops.location import Location, LocationDetails


@dataclass(frozen=True, slots=True)
class LocationList:
    items: list[Location]
    read_only: bool
    """Vrai pour le comptable (« Lecture ») et l'administrateur sous délégation."""


class ManageLocations:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        policy: Policy,
        stock: LocationStock,
        clock: Clock,
    ) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._stock = stock
        self._clock = clock

    def list(self, actor: Actor) -> LocationList:
        access = self._policy.require(actor, Permission.LOCATION_READ)
        with self._uow_factory(actor_shop(actor)) as uow:
            items = LocationRepository.within(uow).list_all()
        return LocationList(items, read_only=access is Access.READ)

    def create(
        self, actor: Actor, details: LocationDetails, location_id: LocationId | None = None
    ) -> tuple[Location, bool]:
        self._policy.require(actor, Permission.LOCATION_MANAGE)
        with self._uow_factory(actor_shop(actor)) as uow:
            locations = LocationRepository.within(uow)
            existing = None if location_id is None else locations.find(location_id)
            if existing is not None:
                return existing, False
            location = Location.create(
                uow.shop_id,
                details,
                performer=performer_of(actor),
                now=self._clock.now(),
                location_id=location_id,
            )
            locations.add(location)
            uow.commit()
        return location, True

    def update(
        self,
        actor: Actor,
        location_id: LocationId,
        patch: Mapping[str, Any],
        version: int,
    ) -> Location:
        self._policy.require(actor, Permission.LOCATION_MANAGE)
        with self._uow_factory(actor_shop(actor)) as uow:
            locations = LocationRepository.within(uow)
            location = locations.get(location_id)
            require_version(location.version, version)
            details = replace(location.details, **patch)
            self._check_withdrawal(uow, location, details)
            if location.change(details, performer=performer_of(actor), now=self._clock.now()):
                locations.update(location)
                uow.commit()
        return location

    def _check_withdrawal(self, uow: UnitOfWork, location: Location, new: LocationDetails) -> None:
        leaves_sale = location.is_active_point_of_sale and not (new.active and new.is_point_of_sale)
        deactivates = location.active and not new.active
        if not (leaves_sale or deactivates):
            return
        key = str(location.id)
        if leaves_sale:
            others = [
                other
                for other in LocationRepository.within(uow).list_all()
                if other.id != location.id and other.is_active_point_of_sale
            ]
            if not others:
                raise LastPointOfSale
            sellers = MembershipRepository.within(uow).list_all()
            if any(m.active and m.default_location_id == location.id for m in sellers):
                raise LocationInUse(key, "default_location")
        if deactivates:
            if self._stock.has_stock(uow, location.id):
                raise LocationHasStock(key)
            settings = ShopSettingsRepository.within(uow).current()
            if settings.values.reception_location_id == location.id:
                raise LocationInUse(key, "reception_location")
        shops = ShopRepository.within(uow)
        shops.update(shops.current())  # garde : sérialise les retraits concurrents
