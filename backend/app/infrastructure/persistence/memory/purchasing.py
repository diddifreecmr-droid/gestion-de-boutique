"""Adaptateurs mémoire du module Achats (T15) : fournisseurs et achats.

Même sémantique que l'adaptateur SQL (`tests/contracts/test_purchasing_contract.py`) :
unicité `supplier_name` et `purchase_number` par boutique, verrou optimiste, isolation.
"""

from datetime import date

from app.application.purchasing.ports import PurchaseRepository, SupplierRepository, position
from app.domain.purchasing.ids import PurchaseId, SupplierId
from app.domain.purchasing.purchase import Purchase
from app.domain.purchasing.supplier import Supplier
from app.infrastructure.persistence.memory.shops import _Listing


class MemorySupplierRepository(_Listing[SupplierId, Supplier], SupplierRepository):
    table = "suppliers"

    def list_all(self) -> list[Supplier]:
        return self._sorted(key=lambda supplier: (supplier.name_key, supplier.id))


class MemoryPurchaseRepository(_Listing[PurchaseId, Purchase], PurchaseRepository):
    table = "purchases"

    def list_between(self, first_day: date, last_day: date) -> list[Purchase]:
        found = self._sorted(key=position)
        found.reverse()
        return [p for p in found if first_day <= p.details.purchase_date <= last_day]

    def for_supplier(self, supplier_id: SupplierId) -> list[Purchase]:
        return [p for p in self._sorted(key=position) if p.details.supplier_id == supplier_id]


MEMORY_PURCHASING_REPOSITORIES = (MemorySupplierRepository, MemoryPurchaseRepository)
