"""Adaptateurs mémoire du stock (T14) : projection, grand livre (ajout seul), ajustements,
inventaires. Même sémantique que l'adaptateur SQL (`tests/contracts/test_stock_contract.py`).

Concurrence : la projection est un agrégat versionné ; deux transactions qui la modifient
s'excluent au `commit` (`VersionConflict`), deux créations du même couple article x lieu par la
contrainte `stock_level_article_location` (`Duplicate`).
"""

from datetime import datetime
from typing import cast
from uuid import UUID

from app.application.ports.pagination import Page, PageRequest, paginate
from app.application.stock.ports import (
    AdjustmentRepository,
    InventoryRepository,
    StockLevelRepository,
    StockMovementLog,
    movement_position,
)
from app.domain.catalog.ids import ArticleId
from app.domain.shops.ids import LocationId
from app.domain.stock.adjustment import Adjustment
from app.domain.stock.ids import AdjustmentId, InventoryId, StockLevelId, StockMovementId
from app.domain.stock.inventory import Inventory
from app.domain.stock.level import StockLevel
from app.domain.stock.movement import StockMovement
from app.domain.stock.values import MovementType
from app.infrastructure.persistence.memory.database import Row
from app.infrastructure.persistence.memory.shop_store import MemoryShopStore
from app.infrastructure.persistence.memory.shops import _Listing

STORED_VERSION = 1


class MemoryStockLevelRepository(_Listing[StockLevelId, StockLevel], StockLevelRepository):
    table = "stock_levels"

    def find_level(self, article_id: ArticleId, location_id: LocationId) -> StockLevel | None:
        found = [lv for lv in self.list_all() if lv.key == (article_id, location_id)]
        return found[0] if found else None

    def for_article(self, article_id: ArticleId) -> list[StockLevel]:
        return [level for level in self.list_all() if level.article_id == article_id]

    def for_location(self, location_id: LocationId) -> list[StockLevel]:
        return [level for level in self.list_all() if level.location_id == location_id]

    def list_all(self) -> list[StockLevel]:
        return self._sorted(key=lambda level: level.id)


class MemoryStockMovementLog(MemoryShopStore, StockMovementLog):
    table = "stock_movements"

    def _append(self, movement: StockMovement) -> None:
        row = Row(
            shop_id=movement.shop_id,
            entity_id=movement.id,
            version=STORED_VERSION,
            unique={},
            payload=movement,  # dataclass gelée : aucune copie à protéger
        )
        self._transaction.insert(self.table, row)

    def _all(self) -> list[StockMovement]:
        # Les lignes de cette table ne sont construites que par `_append`.
        rows = self._transaction.rows(self.table)
        return sorted((cast(StockMovement, row.payload) for row in rows), key=lambda m: m.id)

    def find(self, movement_id: StockMovementId) -> StockMovement | None:
        found = [m for m in self._all() if m.id == movement_id]
        return found[0] if found else None

    def reversal_of(self, movement_id: StockMovementId) -> StockMovement | None:
        found = [m for m in self._all() if m.reverses == movement_id]
        return found[0] if found else None

    def for_source(self, source_id: UUID) -> list[StockMovement]:
        return [m for m in self._all() if m.source.id == source_id]

    def for_article(self, article_id: ArticleId, page: PageRequest) -> Page[StockMovement]:
        mine = [m for m in self._all() if m.article_id == article_id]
        ordered = sorted(mine, key=movement_position, reverse=True)
        return paginate(ordered, page, movement_position)

    def count_sources_since(
        self, location_id: LocationId, movement_type: MovementType, since: datetime
    ) -> int:
        sources = {
            m.source.id
            for m in self._all()
            if m.location_id == location_id and m.type is movement_type and m.recorded_at >= since
        }
        return len(sources)


class MemoryAdjustmentRepository(_Listing[AdjustmentId, Adjustment], AdjustmentRepository):
    table = "stock_adjustments"


class MemoryInventoryRepository(_Listing[InventoryId, Inventory], InventoryRepository):
    table = "inventories"

    def find_open(self, location_id: LocationId) -> Inventory | None:
        found = self._sorted(key=lambda inventory: inventory.id)
        running = [inv for inv in found if inv.open_location_key == location_id]
        return running[0] if running else None


MEMORY_STOCK_REPOSITORIES = (
    MemoryStockLevelRepository,
    MemoryStockMovementLog,
    MemoryAdjustmentRepository,
    MemoryInventoryRepository,
)
