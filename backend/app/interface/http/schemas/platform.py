"""Schémas de la console plateforme (`/platform/shops`, specs § 6.3, recette PLT-01 à 04).

Les bornes ici refusent tôt une saisie absurde (400 `VALIDATION_ERROR`) ; les règles métier
(téléphone, profil, unicité du nom dans le compte) restent celles du domaine.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.plans.entitlements import Entitlement
from app.domain.profiles.modules import Module
from app.domain.shops.values import ShopStatus

TEXT = Field(min_length=1, max_length=120)
PHONE = Field(min_length=1, max_length=32)
OPTIONAL = Field(default=None, max_length=200)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class OwnerRequest(_Strict):
    name: str = TEXT
    phone: str = PHONE


class OpenShopRequest(_Strict):
    profile_code: str = Field(min_length=1, max_length=32, examples=["motos"])
    name: str = TEXT
    city: str = TEXT
    phone: str = PHONE
    address: str | None = OPTIONAL
    niu: str | None = Field(default=None, max_length=32)
    rccm: str | None = Field(default=None, max_length=32)
    owner: OwnerRequest
    account_name: str | None = Field(default=None, max_length=120)


class AdministerShopRequest(_Strict):
    """Champs absents : inchangés. `entitlements[x] = null` retire la surcharge."""

    modules: list[Module] | None = Field(
        default=None,
        description=(
            "Liste **complète** des modules actifs voulus, obligatoires compris (core, audit, "
            "catalog, sales). 422 MODULE_MANDATORY si l'un manque, MODULE_DEPENDENCY si "
            "transport sans transfers, MODULE_NOT_AVAILABLE hors profil."
        ),
    )
    status: ShopStatus | None = None
    entitlements: dict[Entitlement, bool | None] = Field(default_factory=dict)


class ShopSummaryResponse(_Strict):
    shop_id: str
    name: str
    profile_code: str
    city: str
    status: str
    enabled_modules: list[str]
    account_id: str
    account_name: str
    plan: str
    created_at: datetime


class OpenedShopResponse(_Strict):
    shop: ShopSummaryResponse
    owner_id: str
    owner_created: bool
    temporary_pin: str | None
    """Affiché **une seule fois** ; `null` si le propriétaire avait déjà un compte."""


class EntitlementStateResponse(_Strict):
    code: Entitlement
    enabled: bool
    """Valeur en vigueur (offre du compte + surcharge)."""
    override: bool | None
    """Surcharge de l'administrateur ; `null` si l'offre du compte décide."""


class PlatformShopAccessResponse(_Strict):
    """Droits d'offre et délégation du propriétaire (`null` : aucune en cours)."""

    shop_id: str
    entitlements: list[EntitlementStateResponse]
    admin_access_until: datetime | None
