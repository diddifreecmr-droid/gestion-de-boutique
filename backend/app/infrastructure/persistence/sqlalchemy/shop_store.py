"""Gabarit SQL des ports de boutique **sans agrégat** (journal en ajout seul…).

Pendant de `SqlRepository` pour les ports qui n'héritent pas de `Repository` : même
transaction, même registre (`SqlUnitOfWork(repositories=…)`). Chaque requête d'un adaptateur
concret filtre sur `self.shop_id` (specs § 8.3) ; `_own_shop()` fournit ce filtre.
"""

from typing import ClassVar

import sqlalchemy as sa

from app.application.ports.aggregate import AggregateTracker
from app.application.ports.shop_bound import ShopBoundPort
from app.domain.shared.ids import ShopId
from app.infrastructure.persistence.sqlalchemy.transaction import SqlTransaction


class SqlShopStore(ShopBoundPort):
    """Port SQL lié à une boutique et à une transaction ; `table` doit avoir `shop_id`."""

    table: ClassVar[sa.Table]

    def __init__(
        self, shop_id: ShopId, tracker: AggregateTracker, transaction: SqlTransaction
    ) -> None:
        table = getattr(type(self), "table", None)
        if not isinstance(table, sa.Table) or "shop_id" not in table.c:
            msg = f"{type(self).__name__} doit déclarer `table` (sa.Table avec shop_id)"
            raise TypeError(msg)
        super().__init__(shop_id, tracker)
        self._transaction = transaction

    def _own_shop(self) -> sa.ColumnElement[bool]:
        return self.table.c.shop_id == self.shop_id.value
