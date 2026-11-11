"""Agrégat `Membership` : le rôle d'un utilisateur dans une boutique (CDC § 20.1, UC-SOC-04).

- Un seul rattachement par utilisateur et par boutique (contrainte `membership_user`).
- Un seul rôle ; il doit être proposé par le profil (Chauffeur : Motos seulement) — le cas
  d'utilisation passe le profil, l'agrégat refuse (`RoleNotOffered`).
- Lieu de vente habituel : **obligatoire pour un vendeur** et point de vente actif
  (`NotPointOfSale`, MEM-01) ; les autres rôles n'en ont pas (saisie refusée).
- Désactivation (RG-D06) **par boutique** : le compte reste valable dans ses autres boutiques
  (voir `application/shops/use_cases/manage_members.py`). « Au moins un propriétaire actif »
  (RG-D08) regarde tous les rattachements : contrôle du cas d'utilisation.
"""

from dataclasses import dataclass, field
from datetime import datetime

from app.domain.audit.values import EntityRef, FieldChange, Performer
from app.domain.profiles.profile import ShopProfile
from app.domain.shared.errors import InvalidStateTransition, ValidationFailed
from app.domain.shared.events import EventCollector
from app.domain.shared.ids import ShopId, UserId
from app.domain.shared.roles import Role
from app.domain.shops.errors import NotPointOfSale, RoleNotOffered
from app.domain.shops.events import MemberAdded, MemberChanged
from app.domain.shops.ids import LocationId, MembershipId
from app.domain.shops.location import Location


def checked_assignment(
    profile: ShopProfile, role: Role, location: Location | None
) -> LocationId | None:
    """Rôle proposé par le profil et lieu habituel conforme ; renvoie le lieu à retenir."""
    role = Role(role)
    if not profile.offers(role):
        raise RoleNotOffered(role.value, profile.code.value)
    if role is not Role.SELLER:
        if location is not None:
            msg = "Seul un vendeur a un lieu de vente habituel"
            raise ValidationFailed(msg, details={"field": "default_location_id"})
        return None
    if location is None:
        msg = "Lieu de vente habituel obligatoire pour un vendeur"
        raise ValidationFailed(msg, details={"field": "default_location_id"})
    if not location.is_active_point_of_sale:
        raise NotPointOfSale(str(location.id))
    return location.id


@dataclass(eq=False, kw_only=True)
class Membership:
    id: MembershipId
    shop_id: ShopId
    user_id: UserId
    role: Role
    default_location_id: LocationId | None = None
    active: bool = True
    version: int = 0
    events: EventCollector = field(default_factory=EventCollector, repr=False)

    def __post_init__(self) -> None:
        self.role = Role(self.role)
        if (self.role is Role.SELLER) != (self.default_location_id is not None):
            msg = "Un vendeur, et lui seul, a un lieu de vente habituel"
            raise ValueError(msg)

    @property
    def entity(self) -> EntityRef:
        return EntityRef("user", self.user_id.value)

    @property
    def is_active_owner(self) -> bool:
        return self.active and self.role is Role.OWNER

    @classmethod
    def add(
        cls,
        *,
        shop_id: ShopId,
        user_id: UserId,
        role: Role,
        location: Location | None,
        profile: ShopProfile,
        performer: Performer,
        now: datetime,
    ) -> "Membership":
        membership = cls(
            id=MembershipId.new(),
            shop_id=shop_id,
            user_id=user_id,
            role=role,
            default_location_id=checked_assignment(profile, role, location),
        )
        membership.events.record(
            MemberAdded(
                shop_id=shop_id,
                occurred_at=now,
                performer=performer,
                entity=membership.entity,
                summary=f"Utilisateur ajouté ({membership.role.value})",
                changes=(FieldChange("role", None, membership.role.value),),
            )
        )
        return membership

    def assign(
        self,
        role: Role,
        location: Location | None,
        *,
        profile: ShopProfile,
        performer: Performer,
        now: datetime,
    ) -> bool:
        """Nouveau rôle et/ou lieu habituel ; `False` si rien ne change."""
        location_id = checked_assignment(profile, role, location)
        before = (self.role.value, _text(self.default_location_id))
        self.role, self.default_location_id = Role(role), location_id
        after = (self.role.value, _text(self.default_location_id))
        changes = tuple(
            FieldChange(name, old, new)
            for name, old, new in zip(("role", "default_location_id"), before, after, strict=True)
            if old != new
        )
        self._record(changes, "Rôle ou lieu habituel modifié", performer, now)
        return bool(changes)

    def set_active(self, active: bool, *, performer: Performer, now: datetime) -> None:
        """Désactive ou réactive le rattachement (UC-SOC-04) ; rejouer la même valeur → 422."""
        if self.active is active:
            state = "actif" if active else "désactivé"
            msg = f"Ce rattachement est déjà {state}"
            raise InvalidStateTransition(msg, details={"active": active})
        self.active = active
        summary = (
            "Compte réactivé dans la boutique" if active else "Compte désactivé dans la boutique"
        )
        self._record((FieldChange("active", not active, active),), summary, performer, now)

    def _record(
        self, changes: tuple[FieldChange, ...], summary: str, performer: Performer, now: datetime
    ) -> None:
        if changes:
            self.events.record(
                MemberChanged(
                    shop_id=self.shop_id,
                    occurred_at=now,
                    performer=performer,
                    entity=self.entity,
                    summary=summary,
                    changes=changes,
                )
            )


def _text(location: LocationId | None) -> str | None:
    return None if location is None else str(location)
