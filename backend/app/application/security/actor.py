"""Acteur d'un cas d'utilisation (TR-03) et délégation de l'administrateur (specs § 8.3).

Deux formes, exclusives :

- **membre d'une boutique** : `shop_id` et `role` obligatoires (rôle relu par boutique à chaque
  requête, specs § 8.1) ;
- **administrateur plateforme** : aucun rôle de boutique. Il ne voit les données d'une boutique
  que par une `AdminDelegation` non expirée, créée par le propriétaire (24 h, specs § 15.1).

Aucune horloge cachée : l'instant courant est toujours passé en paramètre.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Self

from app.application.security.roles import Role
from app.domain.shared.ids import DeviceId, ShopId, UserId

DEFAULT_DELEGATION_DURATION = timedelta(hours=24)
"""Durée par défaut d'un `ADMIN_ACCESS_GRANT` (décision Q7, specs § 15.1)."""


def require_utc(moment: datetime, name: str) -> datetime:
    """Refuse un instant naïf ou hors UTC : une comparaison ambiguë serait une faille."""
    if not isinstance(moment, datetime):
        msg = f"{name} doit être un datetime, reçu {type(moment).__name__}"
        raise TypeError(msg)
    if moment.utcoffset() != timedelta(0):
        msg = f"{name} doit être un datetime aware en UTC, reçu {moment!r}"
        raise ValueError(msg)
    return moment


@dataclass(frozen=True, slots=True)
class AdminDelegation:
    """Accord du propriétaire : l'admin peut consulter `shop_id` jusqu'à `expires_at` exclu."""

    shop_id: ShopId
    expires_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.shop_id, ShopId):
            msg = "AdminDelegation.shop_id doit être un ShopId"
            raise TypeError(msg)
        require_utc(self.expires_at, "AdminDelegation.expires_at")

    @classmethod
    def granted_at(
        cls, shop_id: ShopId, now: datetime, duration: timedelta = DEFAULT_DELEGATION_DURATION
    ) -> Self:
        if duration <= timedelta(0):
            msg = f"Durée de délégation strictement positive attendue, reçu {duration}"
            raise ValueError(msg)
        return cls(shop_id, require_utc(now, "now") + duration)

    def allows(self, shop_id: ShopId, now: datetime) -> bool:
        """Vrai si la délégation vise `shop_id` et n'a pas expiré à l'instant `now`."""
        return self.shop_id == shop_id and require_utc(now, "now") < self.expires_at


@dataclass(frozen=True, slots=True, kw_only=True)
class Actor:
    """Qui agit, pour quelle boutique, depuis quel appareil. Immuable."""

    user_id: UserId
    device_id: DeviceId
    shop_id: ShopId | None
    role: Role | None
    is_platform_admin: bool = False
    delegation: AdminDelegation | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.user_id, UserId) or not isinstance(self.device_id, DeviceId):
            msg = "Actor exige un UserId et un DeviceId typés"
            raise TypeError(msg)
        if self.shop_id is not None and not isinstance(self.shop_id, ShopId):
            msg = "Actor.shop_id doit être un ShopId"
            raise TypeError(msg)
        if self.is_platform_admin:
            if self.role is not None:
                msg = "Un administrateur plateforme n'a pas de rôle de boutique"
                raise ValueError(msg)
            return
        if self.shop_id is None or not isinstance(self.role, Role):
            msg = "Un membre de boutique a obligatoirement un shop_id et un Role"
            raise ValueError(msg)
        if self.delegation is not None:
            msg = "Seul un administrateur plateforme porte une délégation"
            raise ValueError(msg)

    @classmethod
    def member(cls, *, user_id: UserId, device_id: DeviceId, shop_id: ShopId, role: Role) -> Self:
        return cls(user_id=user_id, device_id=device_id, shop_id=shop_id, role=role)

    @classmethod
    def platform_admin(
        cls,
        *,
        user_id: UserId,
        device_id: DeviceId,
        shop_id: ShopId | None = None,
        delegation: AdminDelegation | None = None,
    ) -> Self:
        """Admin hors boutique (`shop_id=None`, console) ou visant une boutique."""
        return cls(
            user_id=user_id,
            device_id=device_id,
            shop_id=shop_id,
            role=None,
            is_platform_admin=True,
            delegation=delegation,
        )
