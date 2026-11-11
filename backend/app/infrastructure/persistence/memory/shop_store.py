"""Gabarit mémoire des ports de boutique **sans agrégat** (journal en ajout seul…).

Pendant de `MemoryRepository` pour les ports qui n'héritent pas de `Repository` : il reçoit la
même transaction et sert par le même registre (`MemoryUnitOfWork(repositories=…)`). Un
adaptateur concret hérite de ce gabarit **et** de son port, puis nomme sa table :

    class MemoryAuditLog(MemoryShopStore, AuditLog):
        table = "audit_entries"
"""

from typing import ClassVar

from app.application.ports.aggregate import AggregateTracker
from app.application.ports.shop_bound import ShopBoundPort
from app.domain.shared.ids import ShopId
from app.infrastructure.persistence.memory.transaction import MemoryTransaction


class MemoryShopStore(ShopBoundPort):
    """Port mémoire lié à une boutique et à une transaction."""

    table: ClassVar[str]

    def __init__(
        self, shop_id: ShopId, tracker: AggregateTracker, transaction: MemoryTransaction
    ) -> None:
        if not getattr(type(self), "table", ""):
            msg = f"{type(self).__name__} doit déclarer l'attribut de classe `table`"
            raise TypeError(msg)
        super().__init__(shop_id, tracker)
        self._transaction = transaction
