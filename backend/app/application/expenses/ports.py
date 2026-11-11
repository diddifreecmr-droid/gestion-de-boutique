"""Ports du module Dépenses (T18) : dépôts d'agrégats et port de **requête** en lecture seule.

- `ExpenseRepository` : dépense par identifiant ; numéro unique dans la boutique
  (`expense_number`) ; `list_with_tag` sert à la fusion des tags (réécriture des dépenses).
- `TagRepository` : nom unique sans casse (`tag_name`, clé `Tag.name_key`).
- `ExpenseQuery` (UC-DEP-03, TR-21) : liste filtrée paginée et totaux de la période. Lecture
  seule : les dépenses renvoyées ne sont pas suivies par l'unité de travail.

Les noms des `UniqueKey` sont ceux des contraintes SQL (`tables_expenses.py`).
"""

from abc import abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date

from app.application.ports.aggregate import UniqueKey
from app.application.ports.pagination import Cursor, Page, PageRequest
from app.application.ports.shop_bound import ShopBoundPort
from app.application.shops.ports import ShopRecordRepository
from app.domain.expenses.expense import Expense
from app.domain.expenses.ids import ExpenseId, TagId
from app.domain.expenses.tag import Tag
from app.domain.shared.ids import UserId
from app.domain.shops.ids import ExpenseCategoryId, LocationId, PaymentModeId

EXPENSE_NUMBER = "expense_number"
TAG_NAME = "tag_name"


class ExpenseRepository(ShopRecordRepository[ExpenseId, Expense]):
    def unique_keys(self) -> Sequence[UniqueKey[Expense]]:
        return (UniqueKey(EXPENSE_NUMBER, lambda expense: str(expense.number)),)

    @abstractmethod
    def list_with_tag(self, tag_id: TagId) -> list[Expense]:
        """Dépenses portant ce tag (annulées comprises), par ordre de saisie."""


class TagRepository(ShopRecordRepository[TagId, Tag]):
    def unique_keys(self) -> Sequence[UniqueKey[Tag]]:
        return (UniqueKey(TAG_NAME, lambda tag: tag.name_key),)

    @abstractmethod
    def find_by_key(self, key: str) -> Tag | None:
        """Tag dont la clé d'unicité vaut `key` (`tag_key(nom)`), fusionné ou non."""

    @abstractmethod
    def list_all(self) -> list[Tag]:
        """Tous les tags (fusionnés compris), par clé de nom puis identifiant."""


@dataclass(frozen=True, slots=True, kw_only=True)
class ExpenseFilters:
    """Filtres d'UC-DEP-03 ; la période (journées de Douala) est obligatoire et incluse."""

    first_day: date
    last_day: date
    category_id: ExpenseCategoryId | None = None
    tag_id: TagId | None = None
    location_id: LocationId | None = None
    created_by: UserId | None = None
    payment_mode_id: PaymentModeId | None = None


@dataclass(frozen=True, slots=True)
class CategoryTotal:
    category_id: ExpenseCategoryId
    amount: int
    count: int


@dataclass(frozen=True, slots=True)
class ExpenseTotals:
    """Total et répartition par catégorie des dépenses **valides** (RG-T03), par montant."""

    amount: int
    count: int
    by_category: tuple[CategoryTotal, ...] = field(default=())


def position(expense: Expense) -> Cursor:
    """Ordre des listes : du plus récemment saisi au plus ancien (`received_at`, `id`)."""
    return Cursor(expense.capture.received_at, expense.id.value)


class ExpenseQuery(ShopBoundPort):
    @abstractmethod
    def search(self, filters: ExpenseFilters, page: PageRequest) -> Page[Expense]:
        """Dépenses datées (`spent_on`) dans la période, annulées comprises (RG-T03 : visibles)."""

    @abstractmethod
    def totals(self, filters: ExpenseFilters) -> ExpenseTotals:
        """Totaux des mêmes filtres, **hors annulées** ; catégories triées par montant décroissant
        puis identifiant."""
