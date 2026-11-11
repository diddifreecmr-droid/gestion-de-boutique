"""Agrégat `ExpenseCategory` : catégorie de dépense (CDC § 20.6, UC-DEP-01, UC-DEP-02).

T10 crée les catégories **de base** du profil à l'ouverture (Carburant, Repas, Salaire, Loyer,
Autre) ; T18 ajoute leur gestion par le propriétaire : ajout, renommage, désactivation, ordre.

- Une catégorie de base se renomme mais **ne se désactive pas** (`BaseCategoryLocked`, 422).
- `requires_description` : la saisie exige une description (« Autre », UC-DEP-01). C'est une
  propriété de la catégorie, pas de son nom : « Autre » renommée « Divers » la garde.
- Nom unique dans la boutique sans tenir compte de la casse (`name_key`).
"""

from dataclasses import dataclass, field
from datetime import datetime

from app.domain.audit.values import EntityRef, Performer, Scalar
from app.domain.expenses.errors import BaseCategoryLocked
from app.domain.expenses.events import ExpenseCategoryChanged, ExpenseCategoryCreated
from app.domain.shared.events import EventCollector
from app.domain.shared.ids import ShopId
from app.domain.shops.events import diff
from app.domain.shops.ids import ExpenseCategoryId
from app.domain.shops.location import MAX_DISPLAY_ORDER
from app.domain.shops.values import clean_text, name_key, require_int

CATEGORY_NAME_MAX_LENGTH = 60
OTHER_CATEGORY = "Autre"
"""Catégorie de base qui exige une description (CDC § 11, UC-DEP-01)."""


@dataclass(eq=False, kw_only=True)
class ExpenseCategory:
    id: ExpenseCategoryId
    shop_id: ShopId
    name: str
    is_base: bool
    active: bool = True
    display_order: int = 0
    requires_description: bool = False
    version: int = 0
    events: EventCollector = field(default_factory=EventCollector, repr=False)

    def __post_init__(self) -> None:
        self.name = clean_text(self.name, "name", max_length=CATEGORY_NAME_MAX_LENGTH)
        require_int(self.display_order, "display_order", low=0, high=MAX_DISPLAY_ORDER)
        if self.is_base and not self.active:
            msg = "Une catégorie de base se renomme mais ne se désactive pas"
            raise ValueError(msg)
        if not isinstance(self.active, bool) or not isinstance(self.requires_description, bool):
            msg = "ExpenseCategory : active et requires_description sont des booléens"
            raise TypeError(msg)

    @property
    def name_key(self) -> str:
        return name_key(self.name)

    @property
    def entity(self) -> EntityRef:
        return EntityRef("expense_category", self.id.value, self.name)

    @classmethod
    def seed_base(cls, shop_id: ShopId, name: str, display_order: int) -> "ExpenseCategory":
        """Catégorie de base du profil (aucun événement : `ShopOpened` suffit)."""
        return cls(
            id=ExpenseCategoryId.new(),
            shop_id=shop_id,
            name=name,
            is_base=True,
            display_order=display_order,
            requires_description=name == OTHER_CATEGORY,
        )

    @classmethod
    def create(
        cls,
        shop_id: ShopId,
        name: str,
        *,
        display_order: int,
        performer: Performer,
        now: datetime,
        category_id: ExpenseCategoryId | None = None,
    ) -> "ExpenseCategory":
        """Catégorie ajoutée par le propriétaire (UC-DEP-02) : désactivable."""
        category = cls(
            id=category_id or ExpenseCategoryId.new(),
            shop_id=shop_id,
            name=name,
            is_base=False,
            display_order=display_order,
        )
        category.events.record(
            ExpenseCategoryCreated(
                shop_id=shop_id,
                occurred_at=now,
                performer=performer,
                entity=category.entity,
                summary=f"Catégorie de dépense ajoutée : {category.name}",
            )
        )
        return category

    def change(
        self,
        *,
        performer: Performer,
        now: datetime,
        name: str | None = None,
        active: bool | None = None,
        display_order: int | None = None,
    ) -> bool:
        """Renomme, (dés)active ou réordonne ; journalise l'avant/après. `False` si inchangé."""
        new_name = (
            self.name
            if name is None
            else clean_text(name, "name", max_length=CATEGORY_NAME_MAX_LENGTH)
        )
        new_active = self.active if active is None else active
        new_order = self.display_order if display_order is None else display_order
        require_int(new_order, "display_order", low=0, high=MAX_DISPLAY_ORDER)
        if not isinstance(new_active, bool):
            msg = "ExpenseCategory.active doit être un booléen"
            raise TypeError(msg)
        if self.is_base and not new_active:
            raise BaseCategoryLocked(str(self.id))
        before: dict[str, Scalar] = {
            "name": self.name,
            "active": self.active,
            "display_order": self.display_order,
        }
        after: dict[str, Scalar] = {
            "name": new_name,
            "active": new_active,
            "display_order": new_order,
        }
        changes = diff(before, after)
        if not changes:
            return False
        self.name, self.active, self.display_order = new_name, new_active, new_order
        self.events.record(
            ExpenseCategoryChanged(
                shop_id=self.shop_id,
                occurred_at=now,
                performer=performer,
                entity=self.entity,
                summary=f"Catégorie de dépense modifiée : {new_name}",
                changes=changes,
            )
        )
        return True
