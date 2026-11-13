"""Dépôt SQL des lots d'import (T32) : ligne `import_batch` + éléments `import_item`.

Gabarit `SqlRepository` (verrou optimiste sur le lot) ; les éléments sont **réécrits** avec
le lot dans la même transaction, filtrés sur la boutique. `batch_of` passe par l'index
`import_item_shop_entity_idx` (annulation, QC-6).
"""

from typing import Any
from uuid import UUID

import sqlalchemy as sa

from app.application.imports.ports import ImportBatchRepository
from app.domain.imports.batch import Cancellation, ImportBatch, ImportCounts, ImportedItem
from app.domain.imports.ids import ImportBatchId, ImportPreviewId
from app.domain.imports.values import ImportedEntity, ImportKind, ImportStatus
from app.domain.shared.doc_number import DocNumber
from app.domain.shared.ids import ShopId, UserId
from app.infrastructure.persistence.sqlalchemy.columns import from_db, to_db
from app.infrastructure.persistence.sqlalchemy.import_problems import SqlImportProblemLog
from app.infrastructure.persistence.sqlalchemy.shops import SqlListing
from app.infrastructure.persistence.sqlalchemy.tables_imports import import_batch, import_item

ITEMS_PER_INSERT = 1_000
"""6 paramètres par élément : 6 000 par requête, loin des limites de SQLite et PostgreSQL."""


class SqlImportBatchRepository(SqlListing[ImportBatchId, ImportBatch], ImportBatchRepository):
    table = import_batch

    def _to_columns(self, aggregate: ImportBatch) -> dict[str, Any]:
        counts, cancel = aggregate.counts, aggregate.cancellation
        return {
            "number": str(aggregate.number),
            "kind": aggregate.kind.value,
            "preview_id": aggregate.preview_id.value,
            "source_file_key": aggregate.source_file_key,
            "rows_read": counts.rows_read,
            "rows_imported": counts.rows_imported,
            "rows_ignored": counts.rows_ignored,
            "status": aggregate.status.value,
            "imported_by": aggregate.imported_by.value,
            "imported_at": to_db(aggregate.imported_at),
            "cancelled_at": None if cancel is None else to_db(cancel.at),
            "cancelled_by": None if cancel is None else cancel.by.value,
        }

    def _from_row(self, row: sa.RowMapping) -> ImportBatch:
        cancelled = row["cancelled_at"]
        return ImportBatch(
            id=ImportBatchId(row["id"]),
            shop_id=ShopId(row["shop_id"]),
            number=DocNumber.parse(row["number"]),
            kind=ImportKind(row["kind"]),
            preview_id=ImportPreviewId(row["preview_id"]),
            source_file_key=row["source_file_key"],
            counts=ImportCounts(
                rows_read=int(row["rows_read"]),
                rows_imported=int(row["rows_imported"]),
                rows_ignored=int(row["rows_ignored"]),
            ),
            items=self._items(row["id"]),
            imported_by=UserId(row["imported_by"]),
            imported_at=from_db(row["imported_at"]),
            status=ImportStatus(row["status"]),
            cancellation=None
            if cancelled is None
            else Cancellation(from_db(cancelled), UserId(row["cancelled_by"])),
            version=int(row["version"]),
        )

    def _items(self, batch_id: Any) -> tuple[ImportedItem, ...]:
        c = import_item.c
        statement = (
            sa.select(import_item)
            .where(c.import_batch_id == batch_id, c.shop_id == self.shop_id.value)
            .order_by(c.position)
        )
        return tuple(
            ImportedItem(int(r["line"]), ImportedEntity(r["entity_type"]), r["entity_id"])
            for r in self._transaction.fetch_all(statement)
        )

    def _write_items(self, aggregate: ImportBatch, *, replace: bool) -> None:
        c = import_item.c
        if replace:
            self._transaction.write(
                sa.delete(import_item).where(
                    c.import_batch_id == aggregate.id.value, c.shop_id == self.shop_id.value
                )
            )
        if not aggregate.items:
            return
        rows = [
            {
                "import_batch_id": aggregate.id.value,
                "position": position,
                "shop_id": self.shop_id.value,
                "line": item.line,
                "entity_type": item.entity.value,
                "entity_id": item.entity_id,
            }
            for position, item in enumerate(aggregate.items)
        ]
        for start in range(0, len(rows), ITEMS_PER_INSERT):  # sous la limite de paramètres
            self._transaction.write(
                sa.insert(import_item).values(rows[start : start + ITEMS_PER_INSERT])
            )

    def _insert(self, aggregate: ImportBatch) -> None:
        super()._insert(aggregate)
        self._write_items(aggregate, replace=False)

    def _save(self, aggregate: ImportBatch, *, expected_version: int) -> None:
        super()._save(aggregate, expected_version=expected_version)
        self._write_items(aggregate, replace=True)

    def find_by_preview(self, preview_id: ImportPreviewId) -> ImportBatch | None:
        c = self.table.c
        row = self._transaction.fetch_one(
            sa.select(self.table).where(
                c.shop_id == self.shop_id.value, c.preview_id == preview_id.value
            )
        )
        if row is None:
            return None
        found = self._from_row(row)
        self._tracker.track(found, saved=False)
        return found

    def list_all(self) -> list[ImportBatch]:
        c = self.table.c
        return self._select_all(c.imported_at.desc(), c.id.desc())

    def batch_of(self, entity: ImportedEntity, entity_id: UUID) -> ImportBatch | None:
        c = import_item.c
        owner = self._transaction.fetch_one(
            sa.select(c.import_batch_id)
            .where(
                c.shop_id == self.shop_id.value,
                c.entity_type == entity.value,
                c.entity_id == entity_id,
            )
            .limit(1)
        )
        return None if owner is None else self.find(ImportBatchId(owner["import_batch_id"]))


SQL_IMPORT_REPOSITORIES = (SqlImportBatchRepository, SqlImportProblemLog)
