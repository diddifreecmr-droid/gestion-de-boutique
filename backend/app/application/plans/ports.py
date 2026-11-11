"""Ports des droits d'offre (TR-26, D17).

- `Entitlements.is_enabled(shop_id, entitlement)` : seule question posée par les cas
  d'utilisation (via `require_entitlement`) ;
- `ShopPlans` : offre d'une boutique (T10 la lira sur la boutique ; d'ici là, une offre fixe) ;
- `EntitlementOverrides` : surcharges **plateforme** posées par l'administrateur, hors de toute
  boutique et de toute unité de travail de boutique (une écriture = une transaction courte).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from app.domain.plans.entitlements import Entitlement, PlanCode
from app.domain.shared.business_day import require_aware
from app.domain.shared.ids import ShopId, UserId


class Entitlements(ABC):
    @abstractmethod
    def is_enabled(self, shop_id: ShopId, entitlement: Entitlement) -> bool:
        """Le droit est-il ouvert pour cette boutique, à cet instant ?"""


class ShopPlans(ABC):
    @abstractmethod
    def plan_of(self, shop_id: ShopId) -> PlanCode: ...


@dataclass(frozen=True, slots=True, kw_only=True)
class EntitlementOverride:
    """Décision de l'administrateur : `enabled` remplace ce que dit l'offre."""

    shop_id: ShopId
    entitlement: Entitlement
    enabled: bool
    set_by: UserId
    set_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.shop_id, ShopId) or not isinstance(self.set_by, UserId):
            msg = "EntitlementOverride exige un ShopId et un UserId"
            raise TypeError(msg)
        if not isinstance(self.entitlement, Entitlement) or not isinstance(self.enabled, bool):
            msg = "EntitlementOverride exige un Entitlement et un booléen"
            raise TypeError(msg)
        object.__setattr__(self, "set_at", require_aware(self.set_at))


class EntitlementOverrides(ABC):
    @abstractmethod
    def find(self, shop_id: ShopId, entitlement: Entitlement) -> EntitlementOverride | None:
        """Surcharge en vigueur, ou `None` (l'offre décide)."""

    @abstractmethod
    def put(self, override: EntitlementOverride) -> None:
        """Pose ou remplace la surcharge de `(shop_id, entitlement)`, validée aussitôt."""

    @abstractmethod
    def remove(self, shop_id: ShopId, entitlement: Entitlement) -> bool:
        """Retire la surcharge (l'offre décide de nouveau) ; `False` s'il n'y en avait pas."""
