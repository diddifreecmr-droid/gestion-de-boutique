"""Agrégat `ExpenseCategory` : catégorie de dépense (CDC § 20.6, UC-DEP-02).

T10 ne fait que créer les catégories **de base** du profil à l'ouverture (Carburant, Repas,
Salaire, Loyer, Autre). Leur gestion (ajout, renommage, désactivation d'une catégorie qui
n'est pas de base) arrive avec le module Dépenses (T18), sur ce même agrégat.
"""

from dataclasses import dataclass, field

from app.domain.shared.events import EventCollector
from app.domain.shared.ids import ShopId
from app.domain.shops.ids import ExpenseCategoryId
from app.domain.shops.location import MAX_DISPLAY_ORDER
from app.domain.shops.values import clean_text, name_key, require_int

CATEGORY_NAME_MAX_LENGTH = 60


@dataclass(eq=False, kw_only=True)
class ExpenseCategory:
    id: ExpenseCategoryId
    shop_id: ShopId
    name: str
    is_base: bool
    active: bool = True
    display_order: int = 0
    version: int = 0
    events: EventCollector = field(default_factory=EventCollector, repr=False)

    def __post_init__(self) -> None:
        self.name = clean_text(self.name, "name", max_length=CATEGORY_NAME_MAX_LENGTH)
        require_int(self.display_order, "display_order", low=0, high=MAX_DISPLAY_ORDER)
        if self.is_base and not self.active:
            msg = "Une catégorie de base se renomme mais ne se désactive pas"
            raise ValueError(msg)

    @property
    def name_key(self) -> str:
        return name_key(self.name)

    @classmethod
    def seed_base(cls, shop_id: ShopId, name: str, display_order: int) -> "ExpenseCategory":
        return cls(
            id=ExpenseCategoryId.new(),
            shop_id=shop_id,
            name=name,
            is_base=True,
            display_order=display_order,
        )
