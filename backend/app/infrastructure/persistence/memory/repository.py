"""Gabarit de dépôt mémoire : implémente les trois primitives du port `Repository`.

Un dépôt concret hérite de ce gabarit **et** de son port, puis nomme sa table :

    class MemoryWidgetRepository(MemoryRepository[WidgetId, Widget], WidgetRepository):
        table = "widgets"

Les agrégats sont **copiés** à l'écriture comme à la lecture (`copy.deepcopy`) : l'appelant ne
peut jamais modifier l'état stocké sans passer par `update`, comme avec une vraie base. La copie
stockée est purgée de ses événements en attente (ils appartiennent à l'agrégat de l'appelant).
"""

import copy
from typing import ClassVar, cast

from app.application.ports.aggregate import Aggregate, AggregateTracker
from app.application.ports.repository import Repository
from app.domain.shared.ids import EntityId, ShopId
from app.infrastructure.persistence.memory.database import Row
from app.infrastructure.persistence.memory.transaction import MemoryTransaction


class MemoryRepository[IdT: EntityId, AggT: Aggregate](Repository[IdT, AggT]):
    """Dépôt mémoire générique, lié à une boutique et à une transaction."""

    table: ClassVar[str]

    def __init__(
        self, shop_id: ShopId, tracker: AggregateTracker, transaction: MemoryTransaction
    ) -> None:
        if not getattr(type(self), "table", ""):
            msg = f"{type(self).__name__} doit déclarer l'attribut de classe `table`"
            raise TypeError(msg)
        super().__init__(shop_id, tracker)
        self._transaction = transaction

    def _load(self, entity_id: IdT) -> AggT | None:
        row = self._transaction.load(self.table, entity_id)
        if row is None:
            return None
        # La ligne n'a été construite que par `_row` à partir d'un AggT de ce même dépôt.
        return cast(AggT, copy.deepcopy(row.payload))

    def _insert(self, aggregate: AggT) -> None:
        self._transaction.insert(self.table, self._row(aggregate))

    def _save(self, aggregate: AggT, *, expected_version: int) -> None:
        self._transaction.update(self.table, self._row(aggregate), expected_version)

    def _row(self, aggregate: AggT) -> Row:
        snapshot = copy.deepcopy(aggregate)
        snapshot.events.pull()
        unique = {
            key.name: value
            for key in self.unique_keys()
            if (value := key.extract(aggregate)) is not None
        }
        return Row(
            shop_id=aggregate.shop_id,
            entity_id=aggregate.id,
            version=aggregate.version,
            unique=unique,
            payload=snapshot,
        )
