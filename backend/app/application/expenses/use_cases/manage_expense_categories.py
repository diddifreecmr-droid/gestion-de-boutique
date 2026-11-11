"""UC-DEP-02 — Gérer les catégories de dépense (recette EXP-03, M24).

- Lister : comptable et propriétaire (`EXPENSE_READ`) ; le comptable choisit parmi les
  catégories **actives**, le propriétaire (`EXPENSE_CATEGORY_MANAGE`) les voit toutes.
- Ajouter, renommer, désactiver, réordonner : propriétaire seul (comptable → 403). Les 5
  catégories de base se renomment mais ne se désactivent pas (`BASE_CATEGORY_LOCKED`, 422).
  Nom unique sans casse (409 `DUPLICATE`). Chaque changement est journalisé (« Régler »).
- Création idempotente : un `category_id` déjà connu renvoie la catégorie (`created=False`).
"""

from dataclasses import dataclass

from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWorkFactory
from app.application.security.access import Access
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.security.role_matrix import access_for
from app.application.shops.context import actor_shop, performer_of, require_version
from app.application.shops.ports import ExpenseCategoryRepository
from app.domain.shops.expense_category import ExpenseCategory
from app.domain.shops.ids import ExpenseCategoryId


@dataclass(frozen=True, slots=True, kw_only=True)
class CategoryPatch:
    """Champs à changer (`None` = inchangé)."""

    name: str | None = None
    active: bool | None = None
    display_order: int | None = None


class ManageExpenseCategories:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock

    def list(self, actor: Actor) -> list[ExpenseCategory]:
        self._policy.require(actor, Permission.EXPENSE_READ)
        with self._uow_factory(actor_shop(actor)) as uow:
            categories = ExpenseCategoryRepository.within(uow).list_all()
        if self._manages(actor):
            return categories
        return [category for category in categories if category.active]

    def create(
        self,
        actor: Actor,
        name: str,
        display_order: int | None = None,
        category_id: ExpenseCategoryId | None = None,
    ) -> tuple[ExpenseCategory, bool]:
        self._policy.require(actor, Permission.EXPENSE_CATEGORY_MANAGE)
        with self._uow_factory(actor_shop(actor)) as uow:
            categories = ExpenseCategoryRepository.within(uow)
            existing = None if category_id is None else categories.find(category_id)
            if existing is not None:
                return existing, False
            order = display_order
            if order is None:  # à la suite des catégories existantes
                order = max((c.display_order for c in categories.list_all()), default=0) + 1
            category = ExpenseCategory.create(
                uow.shop_id,
                name,
                display_order=order,
                performer=performer_of(actor),
                now=self._clock.now(),
                category_id=category_id,
            )
            categories.add(category)
            uow.commit()
        return category, True

    def update(
        self, actor: Actor, category_id: ExpenseCategoryId, patch: CategoryPatch, version: int
    ) -> ExpenseCategory:
        self._policy.require(actor, Permission.EXPENSE_CATEGORY_MANAGE)
        with self._uow_factory(actor_shop(actor)) as uow:
            categories = ExpenseCategoryRepository.within(uow)
            category = categories.get(category_id)
            require_version(category.version, version)
            changed = category.change(
                performer=performer_of(actor),
                now=self._clock.now(),
                name=patch.name,
                active=patch.active,
                display_order=patch.display_order,
            )
            if changed:
                categories.update(category)
                uow.commit()
        return category

    @staticmethod
    def _manages(actor: Actor) -> bool:
        """Le propriétaire voit aussi les catégories désactivées ; l'admin délégué non."""
        if actor.role is None:
            return False
        return access_for(actor.role, Permission.EXPENSE_CATEGORY_MANAGE) is Access.ALL
