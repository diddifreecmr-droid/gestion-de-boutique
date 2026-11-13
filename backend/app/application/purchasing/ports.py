"""Ports du module Achats (T15) : fournisseurs et achats, liés à la boutique.

- `SupplierRepository` : nom unique sans casse (`supplier_name`, clé `Supplier.name_key`).
- `PurchaseRepository` : numéro unique (`purchase_number`) ; `list_between` lit les achats
  **datés** (date d'achat, pas de saisie) dans une période, annulés compris (RG-T03 : visibles,
  exclus des totaux par le cas d'utilisation).

Les noms des `UniqueKey` sont ceux des contraintes SQL (`tables_purchasing.py`).
"""

from abc import abstractmethod
from collections.abc import Sequence
from datetime import date

from app.application.ports.aggregate import UniqueKey
from app.application.ports.pagination import Cursor
from app.application.shops.ports import ShopRecordRepository
from app.domain.purchasing.ids import PurchaseId, SupplierId
from app.domain.purchasing.purchase import Purchase
from app.domain.purchasing.supplier import Supplier

SUPPLIER_NAME = "supplier_name"
PURCHASE_NUMBER = "purchase_number"


class SupplierRepository(ShopRecordRepository[SupplierId, Supplier]):
    def unique_keys(self) -> Sequence[UniqueKey[Supplier]]:
        return (UniqueKey(SUPPLIER_NAME, lambda supplier: supplier.unique_name),)

    @abstractmethod
    def list_all(self) -> list[Supplier]:
        """Tous les fournisseurs (inactifs et retirés compris), par clé de nom puis id."""


class PurchaseRepository(ShopRecordRepository[PurchaseId, Purchase]):
    def unique_keys(self) -> Sequence[UniqueKey[Purchase]]:
        return (UniqueKey(PURCHASE_NUMBER, lambda purchase: str(purchase.number)),)

    @abstractmethod
    def list_between(self, first_day: date, last_day: date) -> list[Purchase]:
        """Achats dont la date d'achat est dans `[first_day, last_day]`, ordre `position`
        décroissant (plus récent d'abord)."""

    @abstractmethod
    def for_supplier(self, supplier_id: SupplierId) -> list[Purchase]:
        """Achats du fournisseur (annulés compris), ordre `position` croissant."""


def position(purchase: Purchase) -> Cursor:
    """Ordre des listes (UC-ACH-05) : date d'achat décroissante (instant d'entrée), puis `id`."""
    return Cursor(purchase.entry_instant, purchase.id.value)
