"""Dépôts mémoire de l'import : même sémantique que les adaptateurs SQL (contrats T32, T35)."""

from typing import cast
from uuid import UUID

from app.application.imports.ports import ImportBatchRepository, ImportProblemLog
from app.domain.imports.batch import ImportBatch
from app.domain.imports.ids import ImportBatchId, ImportPreviewId
from app.domain.imports.problems import RowError
from app.domain.imports.values import ImportedEntity
from app.infrastructure.persistence.memory.database import Row
from app.infrastructure.persistence.memory.shop_store import MemoryShopStore
from app.infrastructure.persistence.memory.shops import _Listing

STORED_VERSION = 1


class MemoryImportBatchRepository(_Listing[ImportBatchId, ImportBatch], ImportBatchRepository):
    table = "import_batches"

    def find_by_preview(self, preview_id: ImportPreviewId) -> ImportBatch | None:
        found = [b for b in self._sorted(key=lambda b: b.id) if b.preview_id == preview_id]
        return found[0] if found else None

    def list_all(self) -> list[ImportBatch]:
        return self._sorted(key=lambda batch: (batch.imported_at, batch.id))[::-1]

    def batch_of(self, entity: ImportedEntity, entity_id: UUID) -> ImportBatch | None:
        for batch in self._sorted(key=lambda b: b.id):
            if any((i.entity, i.entity_id) == (entity, entity_id) for i in batch.items):
                return batch
        return None


class MemoryImportProblemLog(MemoryShopStore, ImportProblemLog):
    table = "import_problems"

    def _append(self, batch_id: ImportBatchId, problems: tuple[RowError, ...]) -> None:
        if not problems:
            return  # rien à garder (comme l'adaptateur SQL : aucune ligne écrite)
        row = Row(
            shop_id=self.shop_id,
            entity_id=batch_id,
            version=STORED_VERSION,
            unique={},
            payload=problems,  # tuple de valeurs gelées : aucune copie à protéger
        )
        self._transaction.insert(self.table, row)

    def for_batch(self, batch_id: ImportBatchId) -> list[RowError]:
        rows = [row for row in self._transaction.rows(self.table) if row.entity_id == batch_id]
        # Les lignes de cette table ne sont construites que par `_append`.
        return [] if not rows else list(cast(tuple[RowError, ...], rows[0].payload))


MEMORY_IMPORT_REPOSITORIES = (MemoryImportBatchRepository, MemoryImportProblemLog)
