"""Adaptateurs SQL du stock (T14, 2/2) : ajustements et inventaires (avec leurs lignes).

Un inventaire est enregistré **d'un bloc** : la ligne `inventory` suit le gabarit
`SqlRepository` (verrou optimiste), puis ses `inventory_line` sont réécrites dans la même
transaction (le verrou de la ligne mère protège ses lignes).
"""

from typing import Any
from uuid import UUID

import sqlalchemy as sa

from app.application.stock.ports import AdjustmentRepository, InventoryRepository
from app.domain.catalog.ids import ArticleId, AttachmentId
from app.domain.shared.doc_number import DocNumber
from app.domain.shared.ids import EntityId, ShopId, UserId
from app.domain.shared.money import Money
from app.domain.shared.quantity import StockUnit
from app.domain.shops.ids import LocationId
from app.domain.stock.adjustment import Adjustment, AdjustmentDirection, AdjustmentReason
from app.domain.stock.ids import AdjustmentId, InventoryId
from app.domain.stock.inventory import Inventory, InventoryStatus
from app.domain.stock.inventory_line import InventoryLine
from app.domain.stock.values import StockCondition
from app.infrastructure.persistence.sqlalchemy import tables_stock as t
from app.infrastructure.persistence.sqlalchemy.columns import from_db, from_db_optional, to_db
from app.infrastructure.persistence.sqlalchemy.shops import SqlListing
from app.infrastructure.persistence.sqlalchemy.stock import (
    SqlStockLevelRepository,
    SqlStockMovementLog,
    optional_quantity,
    quantity,
)


def _uuid(value: EntityId | None) -> UUID | None:
    return None if value is None else value.value


class SqlAdjustmentRepository(SqlListing[AdjustmentId, Adjustment], AdjustmentRepository):
    table = t.stock_adjustment

    def _to_columns(self, aggregate: Adjustment) -> dict[str, Any]:
        return {
            "location_id": aggregate.location_id.value,
            "article_id": aggregate.article_id.value,
            "direction": aggregate.direction.value,
            "unit": aggregate.quantity.unit.value,
            "quantity": aggregate.quantity.value,
            "condition": aggregate.condition.value,
            "reason": aggregate.reason.value,
            "note": aggregate.note,
            "photo_id": _uuid(aggregate.photo_id),
            "inventory_id": _uuid(aggregate.inventory_id),
            "created_at": to_db(aggregate.created_at),
            "author_id": aggregate.author_id.value,
        }

    def _from_row(self, row: sa.RowMapping) -> Adjustment:
        photo, inventory = row["photo_id"], row["inventory_id"]
        return Adjustment(
            id=AdjustmentId(row["id"]),
            shop_id=ShopId(row["shop_id"]),
            location_id=LocationId(row["location_id"]),
            article_id=ArticleId(row["article_id"]),
            direction=AdjustmentDirection(row["direction"]),
            quantity=quantity(row["quantity"], StockUnit(row["unit"])),
            condition=StockCondition(row["condition"]),
            reason=AdjustmentReason(row["reason"]),
            note=row["note"],
            photo_id=None if photo is None else AttachmentId(photo),
            inventory_id=None if inventory is None else InventoryId(inventory),
            created_at=from_db(row["created_at"]),
            author_id=UserId(row["author_id"]),
            version=int(row["version"]),
        )


class SqlInventoryRepository(SqlListing[InventoryId, Inventory], InventoryRepository):
    table = t.inventory

    def _to_columns(self, aggregate: Inventory) -> dict[str, Any]:
        return {
            "number": str(aggregate.number),
            "location_id": aggregate.location_id.value,
            "open_location_id": _uuid(aggregate.open_location_key),
            "status": aggregate.status.value,
            "started_at": to_db(aggregate.started_at),
            "closed_at": None if aggregate.closed_at is None else to_db(aggregate.closed_at),
            "global_reason": aggregate.global_reason,
        }

    def _from_row(self, row: sa.RowMapping) -> Inventory:
        lines = t.inventory_line
        statement = (
            sa.select(lines)
            .where(lines.c.inventory_id == row["id"], lines.c.shop_id == self.shop_id.value)
            .order_by(lines.c.article_id)
        )
        read = {}
        for line in self._transaction.fetch_all(statement):
            unit, value = StockUnit(line["unit"]), line["gap_value"]
            article_id = ArticleId(line["article_id"])
            read[article_id] = InventoryLine(
                article_id=article_id,
                unit=unit,
                counted=optional_quantity(line["counted"], unit),
                theoretical=optional_quantity(line["theoretical"], unit),
                reason=line["reason"],
                gap_value=None if value is None else Money(int(value)),
            )
        return Inventory(
            id=InventoryId(row["id"]),
            shop_id=ShopId(row["shop_id"]),
            number=DocNumber.parse(row["number"]),
            location_id=LocationId(row["location_id"]),
            started_at=from_db(row["started_at"]),
            lines=read,
            status=InventoryStatus(row["status"]),
            closed_at=from_db_optional(row["closed_at"]),
            global_reason=row["global_reason"],
            version=int(row["version"]),
        )

    def _insert(self, aggregate: Inventory) -> None:
        super()._insert(aggregate)
        self._write_lines(aggregate)

    def _save(self, aggregate: Inventory, *, expected_version: int) -> None:
        super()._save(aggregate, expected_version=expected_version)
        lines = t.inventory_line
        self._transaction.write(
            sa.delete(lines).where(
                lines.c.inventory_id == aggregate.id.value, lines.c.shop_id == self.shop_id.value
            )
        )
        self._write_lines(aggregate)

    def _write_lines(self, aggregate: Inventory) -> None:
        rows = [
            {
                "inventory_id": aggregate.id.value,
                "article_id": line.article_id.value,
                "shop_id": aggregate.shop_id.value,
                "unit": line.unit.value,
                "counted": None if line.counted is None else line.counted.value,
                "theoretical": None if line.theoretical is None else line.theoretical.value,
                "reason": line.reason,
                "gap_value": None if line.gap_value is None else line.gap_value.amount,
            }
            for line in aggregate.lines.values()
        ]
        if rows:
            self._transaction.write(sa.insert(t.inventory_line).values(rows))

    def find_open(self, location_id: LocationId) -> Inventory | None:
        found = self._select_all(
            self.table.c.id, where=self.table.c.open_location_id == location_id.value
        )
        return found[0] if found else None


SQL_STOCK_REPOSITORIES = (
    SqlStockLevelRepository,
    SqlStockMovementLog,
    SqlAdjustmentRepository,
    SqlInventoryRepository,
)
