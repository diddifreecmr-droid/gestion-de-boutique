"""Agrégat `MerchantAccount` : le client de la plateforme (CDC § 20.1 « Compte commerçant »).

Agrégat **plateforme** (sans boutique), servi par l'unité de travail plateforme comme `User`.

- Offre (`plan`) : gratuite permanente par défaut (CDC § 1.1) ; elle décide des droits d'offre
  de **toutes** ses boutiques (TR-26), sauf surcharge de l'administrateur.
- Le nom d'une boutique est unique **dans le compte** : le compte garde le nom de chacune de
  ses boutiques (`shop_names`) et refuse un doublon (`Duplicate`, contrainte
  `shop_name_in_account`). Le verrou optimiste du compte sérialise deux ouvertures
  concurrentes : la seconde reçoit `VERSION_CONFLICT`, jamais un doublon.
- Aucun événement : l'ouverture d'une boutique est journalisée **dans** la boutique
  (`ShopOpened`). `events` existe pour le contrat des dépôts plateforme.
"""

from dataclasses import dataclass, field

from app.domain.identity.events import IdentityEvents
from app.domain.identity.phone import PhoneNumber
from app.domain.plans.entitlements import PlanCode
from app.domain.shared.errors import Duplicate
from app.domain.shared.ids import ShopId
from app.domain.shops.ids import MerchantAccountId
from app.domain.shops.values import AccountStatus, clean_text, name_key

SHOP_NAME_IN_ACCOUNT = "shop_name_in_account"


@dataclass(eq=False, kw_only=True)
class MerchantAccount:
    id: MerchantAccountId
    name: str
    phone: PhoneNumber
    plan: PlanCode = PlanCode.FREE
    status: AccountStatus = AccountStatus.ACTIVE
    shop_names: dict[ShopId, str] = field(default_factory=dict)
    version: int = 0
    events: IdentityEvents = field(default_factory=IdentityEvents, repr=False)

    def __post_init__(self) -> None:
        self.name = clean_text(self.name, "account_name")
        if not isinstance(self.phone, PhoneNumber):
            msg = "MerchantAccount.phone doit être un PhoneNumber"
            raise TypeError(msg)
        self.plan = PlanCode(self.plan)
        self.status = AccountStatus(self.status)
        self.shop_names = dict(self.shop_names)

    @classmethod
    def create(cls, *, name: str, phone: PhoneNumber) -> "MerchantAccount":
        return cls(id=MerchantAccountId.new(), name=name, phone=phone)

    def register_shop(self, shop_id: ShopId, shop_name: str) -> None:
        """Inscrit une boutique du compte ; `Duplicate` si le nom y est déjà pris."""
        key = name_key(shop_name)
        if shop_id in self.shop_names or any(name_key(n) == key for n in self.shop_names.values()):
            msg = "Une boutique du compte porte déjà ce nom"
            raise Duplicate(msg, details={"constraint": SHOP_NAME_IN_ACCOUNT, "field": "name"})
        self.shop_names = {**self.shop_names, shop_id: shop_name}
