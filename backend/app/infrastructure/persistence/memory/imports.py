"""Dépôt mémoire des lots d'import : même sémantique que l'adaptateur SQL (contrat T32)."""

from app.application.imports.ports import ImportBatchRepository
from app.domain.imports.batch import ImportBatch
from app.domain.imports.ids import ImportBatchId, ImportPreviewId
from app.infrastructure.persistence.memory.shops import _Listing


class MemoryImportBatchRepository(_Listing[ImportBatchId, ImportBatch], ImportBatchRepository):
    table = "import_batches"

    def find_by_preview(self, preview_id: ImportPreviewId) -> ImportBatch | None:
        found = [b for b in self._sorted(key=lambda b: b.id) if b.preview_id == preview_id]
        return found[0] if found else None


MEMORY_IMPORT_REPOSITORIES = (MemoryImportBatchRepository,)
