"""Agrégat `Shop` : un espace séparé, d'un type donné (CDC § 20.1 « Boutique », UC-SOC-01).

- Son identifiant **est** la boutique (`shop_id == id`) : il vit dans les tables de boutique.
- Le type (`profile_code`) ne change plus après la création : aucun mutateur ne le touche.
- Les modules actifs sont fixés par le profil et modifiables par l'administrateur, dans les
  limites du profil, socle et journal toujours compris (`administer`).
- Le nom est unique dans le compte commerçant : c'est le `MerchantAccount` qui le garantit.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime

from app.domain.audit.values import EntityRef, Performer
from app.domain.identity.phone import PhoneNumber
from app.domain.profiles.modules import MANDATORY_MODULES, Module
from app.domain.profiles.profile import ProfileCode
from app.domain.shared.business_day import require_aware
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.events import EventCollector
from app.domain.shared.ids import ShopId
from app.domain.shops.errors import ModuleNotAvailable
from app.domain.shops.events import SettingsChanged, ShopAdministered, ShopOpened, diff
from app.domain.shops.ids import MerchantAccountId
from app.domain.shops.values import ShopStatus, clean_optional, clean_text

NIU_MAX_LENGTH = 32


@dataclass(frozen=True, slots=True, kw_only=True)
class ShopIdentity:
    """En-tête imprimé sur le reçu (UC-SOC-01 étape 2) : ville et téléphone obligatoires."""

    name: str
    city: str
    phone: PhoneNumber
    address: str | None = None
    niu: str | None = None
    rccm: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", clean_text(self.name, "name"))
        object.__setattr__(self, "city", clean_text(self.city, "city"))
        if not isinstance(self.phone, PhoneNumber):
            msg = "ShopIdentity.phone doit être un PhoneNumber"
            raise TypeError(msg)
        object.__setattr__(self, "address", clean_optional(self.address, "address"))
        object.__setattr__(self, "niu", clean_optional(self.niu, "niu", max_length=NIU_MAX_LENGTH))
        object.__setattr__(
            self, "rccm", clean_optional(self.rccm, "rccm", max_length=NIU_MAX_LENGTH)
        )


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
            msg = "Socle et journal sont toujours actifs"
            raise ValueError(msg)

    @property
    def shop_id(self) -> ShopId:
        return self.id

    @property
    def name(self) -> str:
        return self.identity.name

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
            enabled_modules=frozenset(modules),
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
            wanted = frozenset(Module(m) for m in modules) | MANDATORY_MODULES
            unavailable = sorted(wanted - available)
            if unavailable:
                raise ModuleNotAvailable(unavailable[0].value, self.profile_code.value)
            self.enabled_modules = wanted
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

    def update_identity(
        self, identity: ShopIdentity, *, performer: Performer, now: datetime
    ) -> bool:
        """En-tête du reçu (UC-SOC-06) ; le nom reste celui de l'ouverture (unique au compte)."""
        if identity.name != self.identity.name:
            msg = "Le nom de la boutique se change depuis la console plateforme"
            raise ValidationFailed(msg, details={"field": "name"})
        changes = diff(_header(self.identity), _header(identity))
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
            "modules": ",".join(sorted(m.value for m in self.enabled_modules)),
            "status": self.status.value,
        }


def _header(identity: ShopIdentity) -> dict[str, str | None]:
    return {
        "city": identity.city,
        "phone": identity.phone.e164,
        "address": identity.address,
        "niu": identity.niu,
        "rccm": identity.rccm,
    }
