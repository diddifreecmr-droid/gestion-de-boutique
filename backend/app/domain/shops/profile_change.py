"""Changement de type d'une boutique (décision client QC-1 du 2026-11-13, T27) : règles pures.

- **Permis seulement pour une boutique sans données** (`require_empty`) : aucun article,
  mouvement de stock, vente, achat, dépense ni créance, et aucun membre (actif ou non) d'un
  rôle absent du nouveau profil (un Chauffeur pour Prêt-à-porter). Sinon `422
  PROFILE_CHANGE_BLOCKED`, `details.blocking` = nature → nombre (natures non nulles, dans
  l'ordre de `BlockingKind`). Une boutique qui a des données est **recréée** sur le bon profil.
- **Lieux** (`plan_locations`) : chaque lieu du nouveau profil est créé, ou repris s'il existe
  déjà sous ce nom (sans tenir compte de la casse) avec le type, le point de vente et l'ordre
  du profil ; les autres lieux actifs sont désactivés, sauf ceux qui servent encore (lieu de
  vente habituel d'un membre). Le lieu de réception des achats devient celui du profil.
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from enum import StrEnum

from app.domain.profiles.profile import LocationTemplate, ShopProfile
from app.domain.shops.errors import ProfileChangeBlocked
from app.domain.shops.ids import LocationId
from app.domain.shops.location import Location, LocationDetails
from app.domain.shops.membership import Membership
from app.domain.shops.values import name_key


class BlockingKind(StrEnum):
    """Natures de données qui empêchent le changement de type (ordre de `details.blocking`)."""

    ARTICLES = "articles"
    MOVEMENTS = "movements"
    SALES = "sales"
    PURCHASES = "purchases"
    EXPENSES = "expenses"
    RECEIVABLES = "receivables"
    MEMBERS = "members"
    """Membres (actifs ou non) d'un rôle absent du nouveau profil."""


DATA_KINDS: tuple[BlockingKind, ...] = tuple(
    k for k in BlockingKind if k is not BlockingKind.MEMBERS
)
"""Natures comptées par le recensement des données de la boutique (`ShopDataCensus`)."""


def require_empty(
    data: Mapping[BlockingKind, int], members: Iterable[Membership], profile: ShopProfile
) -> None:
    """`ProfileChangeBlocked` si la boutique a des données ou un membre d'un rôle absent."""
    if set(data) != set(DATA_KINDS):
        msg = f"Recensement incomplet : {sorted(set(DATA_KINDS) ^ set(data))}"
        raise ValueError(msg)
    counts = dict(data)
    for kind, count in counts.items():
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            msg = f"Nombre invalide pour {kind} : {count!r}"
            raise ValueError(msg)
    counts[BlockingKind.MEMBERS] = sum(1 for m in members if not profile.offers(m.role))
    blocking = {kind.value: counts[kind] for kind in BlockingKind if counts[kind]}
    if blocking:
        raise ProfileChangeBlocked(blocking, profile.code.value)


@dataclass(frozen=True, slots=True)
class LocationPlan:
    created: tuple[LocationDetails, ...]
    """Lieux du profil absents de la boutique, à créer."""
    changed: tuple[tuple[Location, LocationDetails], ...]
    """Lieux existants repris (détails du profil) ou désactivés, avec leurs nouveaux détails."""


def _details(template: LocationTemplate) -> LocationDetails:
    return LocationDetails(
        name=template.name,
        kind=template.kind,
        is_point_of_sale=template.is_point_of_sale,
        city=template.city,
        display_order=template.display_order,
    )


def plan_locations(
    existing: Sequence[Location], profile: ShopProfile, in_use: frozenset[LocationId]
) -> LocationPlan:
    """Lieux à créer, reprendre et désactiver pour passer à `profile` (voir l'en-tête)."""
    by_key = {location.name_key: location for location in existing}
    wanted = {name_key(template.name): _details(template) for template in profile.locations}
    created, changed = [], []
    for key, details in wanted.items():
        found = by_key.get(key)
        if found is None:
            created.append(details)
        elif found.details != details:
            changed.append((found, details))
    for location in existing:
        if location.name_key in wanted or not location.active or location.id in in_use:
            continue
        changed.append((location, replace(location.details, active=False)))
    return LocationPlan(created=tuple(created), changed=tuple(changed))


def locations_in_use(members: Iterable[Membership]) -> frozenset[LocationId]:
    """Lieux de vente habituels des membres (actifs ou non) : ils restent actifs."""
    return frozenset(m.default_location_id for m in members if m.default_location_id is not None)
