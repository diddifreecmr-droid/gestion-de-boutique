"""Agrégat `Shop` : un espace séparé, d'un type donné (CDC § 20.1 « Boutique », UC-SOC-01).

- Son identifiant **est** la boutique (`shop_id == id`) : il vit dans les tables de boutique.
- Le type (`profile_code`) ne change que par `change_profile` (console, QC-1, T27) : le cas
  d'utilisation `ChangeShopProfile` vérifie d'abord que la boutique n'a aucune donnée.
- Les modules actifs sont fixés par le profil et modifiables par l'administrateur seul, dans
  les limites du profil (`checked_modules`) : obligatoires toujours compris, dépendances
  respectées (`transport` ⇒ `transfers`), à l'ouverture comme au réglage (`administer`).
- `require_module` : 403 `MODULE_DISABLED` si la boutique n'a pas le module.
- Le nom est unique dans le compte commerçant : c'est le `MerchantAccount` qui le garantit.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime

from app.domain.audit.values import EntityRef, Performer
from app.domain.profiles.modules import MANDATORY_MODULES, Module, upcoming_among
from app.domain.profiles.profile import ProfileCode, ShopProfile
from app.domain.shared.business_day import require_aware
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.events import EventCollector
from app.domain.shared.ids import ShopId
from app.domain.shops.errors import ModuleDisabled
from app.domain.shops.events import (
    SettingsChanged,
    ShopAdministered,
    ShopOpened,
    ShopProfileChanged,
    diff,
)
from app.domain.shops.identity import ShopIdentity
from app.domain.shops.ids import MerchantAccountId
from app.domain.shops.modules import checked_modules
from app.domain.shops.values import ShopStatus

__all__ = ["Shop", "ShopIdentity"]


@dataclass(eq=False, kw_only=True)
class Shop:
    id: ShopId
    account_id: MerchantAccountId
    profile_code: ProfileCode
    identity: ShopIdentity
    enabled_modules: frozenset[Module]
    status: ShopStatus
    created_at: datetime
    version: int = 0
    events: EventCollector = field(default_factory=EventCollector, repr=False)

    def __post_init__(self) -> None:
        self.created_at = require_aware(self.created_at)
        self.profile_code = ProfileCode(self.profile_code)
        if not self.enabled_modules >= MANDATORY_MODULES:
            msg = "Socle, journal, catalogue et ventes sont toujours actifs"
            raise ValueError(msg)
        upcoming = upcoming_among(self.enabled_modules)
        if upcoming:
            msg = f"Module à venir actif (migration 0016) : {', '.join(upcoming)}"
            raise ValueError(msg)

    @property
    def shop_id(self) -> ShopId:
        return self.id

    @property
    def name(self) -> str:
        return self.identity.name

    def has_module(self, module: Module) -> bool:
        return Module(module) in self.enabled_modules

    def require_module(self, module: Module) -> None:
        """Lève `ModuleDisabled` (403 `MODULE_DISABLED`) si le module n'est pas actif."""
        if not self.has_module(module):
            raise ModuleDisabled(Module(module).value)

    @property
    def entity(self) -> EntityRef:
        return EntityRef("shop", self.id.value, self.name)

    @classmethod
    def open(
        cls,
        *,
        shop_id: ShopId,
        account_id: MerchantAccountId,
        profile_code: ProfileCode,
        identity: ShopIdentity,
        modules: frozenset[Module],
        performer: Performer,
        now: datetime,
    ) -> "Shop":
        shop = cls(
            id=shop_id,
            account_id=account_id,
            profile_code=profile_code,
            identity=identity,
            enabled_modules=checked_modules(modules, profile=profile_code),
            status=ShopStatus.ACTIVE,
            created_at=now,
        )
        shop.events.record(
            ShopOpened(
                shop_id=shop_id,
                occurred_at=now,
                performer=performer,
                entity=shop.entity,
                summary=f"Boutique ouverte : {identity.name}",
            )
        )
        return shop

    def administer(
        self,
        *,
        modules: Iterable[Module] | None,
        status: ShopStatus | None,
        available: frozenset[Module],
        performer: Performer,
        now: datetime,
    ) -> bool:
        """Modules et statut (console plateforme) ; renvoie `False` si rien ne change."""
        before = self._snapshot()
        if modules is not None:
            self.enabled_modules = checked_modules(
                modules, available=available, profile=self.profile_code
            )
        if status is not None:
            self.status = ShopStatus(status)
        changes = diff(before, self._snapshot())
        if changes:
            self.events.record(
                ShopAdministered(
                    shop_id=self.id,
                    occurred_at=now,
                    performer=performer,
                    entity=self.entity,
                    summary="Boutique réglée par l'administrateur",
                    changes=changes,
                )
            )
        return bool(changes)

    def change_profile(self, profile: ShopProfile, *, performer: Performer, now: datetime) -> bool:
        """Nouveau type (QC-1) : son code et ses modules de départ. `False` si c'est le même."""
        if profile.code is self.profile_code:
            return False
        before = self._snapshot()
        self.profile_code = profile.code
        self.enabled_modules = checked_modules(
            profile.modules, available=profile.available_modules, profile=profile.code
        )
        self.events.record(
            ShopProfileChanged(
                shop_id=self.id,
                occurred_at=now,
                performer=performer,
                entity=self.entity,
                summary=f"Type de boutique changé : {profile.label}",
                changes=diff(before, self._snapshot()),
            )
        )
        return True

    def update_identity(
        self, identity: ShopIdentity, *, performer: Performer, now: datetime
    ) -> bool:
        """En-tête du reçu (UC-SOC-06) ; le nom reste celui de l'ouverture (unique au compte)."""
        if identity.name != self.identity.name:
            msg = "Le nom de la boutique se change depuis la console plateforme"
            raise ValidationFailed(msg, details={"field": "name"})
        changes = diff(self.identity.header(), identity.header())
        if not changes:
            return False
        self.identity = identity
        self.events.record(
            SettingsChanged(
                shop_id=self.id,
                occurred_at=now,
                performer=performer,
                entity=self.entity,
                summary="En-tête du reçu modifié",
                changes=changes,
            )
        )
        return True

    def _snapshot(self) -> dict[str, str]:
        return {
            "profile_code": self.profile_code.value,
            "modules": ",".join(sorted(m.value for m in self.enabled_modules)),
            "status": self.status.value,
        }
