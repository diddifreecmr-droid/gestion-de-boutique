"""Forme du jeu de démonstration : boutiques, comptes, articles stockés et options de vente.

Les données propres à chaque type de boutique vivent dans `motos.py`, `apparel.py` et
`textile.py` ; le déroulé (ouverture, achats, ventes, dépenses) dans `scenario.py`.
"""

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from app.application.security.actor import Actor
from app.domain.catalog.ids import ArticleId
from app.domain.profiles.profile import ProfileCode
from app.domain.purchasing.units import EntryUnit
from app.domain.sales.lines import SaleMode, round_franc
from app.domain.shared.roles import Role
from app.interface.http.routes.catalog import CatalogComponents


@dataclass(frozen=True, slots=True)
class Person:
    label: str
    """Rôle affiché dans le tableau final (« Gérant », « Employé », « Comptable »…)."""
    name: str
    phone: str
    role: Role
    pin: str
    """Code provisoire connu (6 chiffres, non simple) : à changer à la 1re connexion."""


@dataclass(frozen=True, slots=True)
class SaleOption:
    quantity: Decimal
    unit_price: int
    mode: SaleMode | None = None

    @property
    def amount(self) -> int:
        return round_franc(self.quantity * self.unit_price).amount


@dataclass(frozen=True, slots=True)
class StockedItem:
    article_id: ArticleId
    opening: Decimal
    """Quantité du stock initial, dans l'unité de saisie `entry_unit`."""
    unit_cost: int
    """Coût d'achat par unité de saisie (FCFA)."""
    sales: tuple[SaleOption, ...]
    entry_unit: EntryUnit | None = None
    restock: Decimal = Decimal(2)


CatalogBuilder = Callable[[CatalogComponents, Actor], list[StockedItem]]
"""Crée les articles par les cas d'utilisation du catalogue (comme le gérant)."""


@dataclass(frozen=True, slots=True)
class Expense:
    category: str
    amount: int
    description: str
    days_ago: int


@dataclass(frozen=True, slots=True)
class ShopPlan:
    profile: ProfileCode
    name: str
    city: str
    phone: str
    owner: Person
    sellers: tuple[Person, Person]
    accountant: Person
    suppliers: tuple[str, ...]
    expenses: tuple[Expense, Expense]
    catalog: CatalogBuilder
    customer: tuple[str, str]
    """Client de la vente à crédit (nom, téléphone)."""

    @property
    def people(self) -> tuple[Person, ...]:
        return (self.owner, *self.sellers, self.accountant)


def staff(
    shop: int, labels: tuple[str, str, str, str], names: tuple[str, ...]
) -> tuple[Person, ...]:
    """Gérant, deux employés, comptable : numéros 690001<boutique>0<rang>, codes distincts."""
    roles = (Role.OWNER, Role.SELLER, Role.SELLER, Role.ACCOUNTANT)
    pins = ("482915", "593026", "604137", "715248")
    return tuple(
        Person(label, name, f"690001{shop}0{rank + 1}", role, f"{shop}{pin[1:]}")
        for rank, (label, name, role, pin) in enumerate(
            zip(labels, names, roles, pins, strict=True)
        )
    )


def options(*pairs: tuple[Decimal | int, int, SaleMode | None]) -> tuple[SaleOption, ...]:
    return tuple(SaleOption(Decimal(q), price, mode) for q, price, mode in pairs)
