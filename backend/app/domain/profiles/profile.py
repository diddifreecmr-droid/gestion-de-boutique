"""`ShopProfile` : ce qu'un type de boutique fixe au départ (specs § 4.5, CDC § 3.2, § 17 à 19).

Objet **immuable**, versionné dans le code (`version` augmente à chaque changement de contenu) ;
la boutique garde son `profile_code` et ses surcharges (modules, réglages). Toute incohérence
(lieu de réception inconnu, rôle sans menu, aucun point de vente…) lève `ValueError` dès
l'import du module de profil : un profil faux ne peut pas être livré.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.domain.profiles.fields import FieldSpec
from app.domain.profiles.menus import MenuEntry
from app.domain.profiles.modules import MANDATORY_MODULES, Module, broken_dependencies
from app.domain.profiles.printing import ReceiptFormat
from app.domain.shared.quantity import StockUnit
from app.domain.shared.roles import Role
from app.domain.shops.values import LocationKind


class ProfileCode(StrEnum):
    MOTOS = "motos"
    """Motos et camions (Lot 1, complet)."""
    APPAREL = "apparel"
    """Prêt-à-porter (Lot 3)."""
    TEXTILE = "textile"
    """Textile : pagnes, tissus (Lot 3)."""


@dataclass(frozen=True, slots=True)
class LocationTemplate:
    name: str
    kind: LocationKind
    is_point_of_sale: bool
    city: str | None
    display_order: int

    def __post_init__(self) -> None:
        if self.is_point_of_sale and self.kind is not LocationKind.STORE:
            msg = f"Lieu {self.name} : seul un lieu « Boutique » est point de vente"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class PaymentModeTemplate:
    name: str
    reference_required: bool


@dataclass(frozen=True, slots=True)
class SettingsDefaults:
    """Réglages de départ (CDC § 20.1 « Réglages de la boutique »)."""

    receipt_format: ReceiptFormat
    copies: int = 1
    low_stock_threshold: Decimal = Decimal(2)
    min_price_enabled: bool = False
    exchange_days: int | None = None
    truck_silent_hours: int | None = None
    transfer_in_transit_days: int | None = 7


@dataclass(frozen=True, slots=True, kw_only=True)
class ShopProfile:
    code: ProfileCode
    version: int
    label: str
    modules: frozenset[Module]
    """Modules actifs à l'ouverture."""
    available_modules: frozenset[Module]
    """Modules que l'administrateur peut activer pour ce type."""
    roles: tuple[Role, ...]
    role_labels: Mapping[Role, str]
    menus: Mapping[Role, tuple[MenuEntry, ...]]
    article_fields: tuple[FieldSpec, ...]
    sale_fields: tuple[FieldSpec, ...]
    stock_units: tuple[StockUnit, ...]
    locations: tuple[LocationTemplate, ...]
    reception_location: str
    """Nom du lieu de réception des achats par défaut (Q-01 : réglage de la boutique)."""
    expense_categories: tuple[str, ...]
    payment_modes: tuple[PaymentModeTemplate, ...]
    settings: SettingsDefaults

    def __post_init__(self) -> None:
        problems = list(self._problems())
        if problems:
            msg = f"Profil {self.code} incohérent : {'; '.join(problems)}"
            raise ValueError(msg)

    def _problems(self) -> list[str]:
        problems = []
        if self.version < 1:
            problems.append("version ≥ 1")
        if not MANDATORY_MODULES <= self.modules <= self.available_modules:
            problems.append("modules ⊄ disponibles ou modules obligatoires absents")
        if broken_dependencies(self.modules):
            problems.append("dépendances de modules non tenues (transport ⇒ transfers)")
        if Role.OWNER not in self.roles or len(set(self.roles)) != len(self.roles):
            problems.append("rôles sans propriétaire ou en double")
        if set(self.role_labels) != set(self.roles) or set(self.menus) != set(self.roles):
            problems.append("chaque rôle a un libellé et un menu")
        names = [location.name for location in self.locations]
        if len({name.casefold() for name in names}) != len(names):
            problems.append("noms de lieux en double")
        if not any(location.is_point_of_sale for location in self.locations):
            problems.append("au moins un point de vente")
        if self.reception_location not in names:
            problems.append("lieu de réception absent des lieux")
        if not self.payment_modes or not self.expense_categories or not self.stock_units:
            problems.append("modes de paiement, catégories et unités obligatoires")
        return problems

    def offers(self, role: Role) -> bool:
        return role in self.roles

    def role_label(self, role: Role) -> str:
        return self.role_labels[role]
