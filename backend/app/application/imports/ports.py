"""Ports de l'import (specs § 9 « Excel ») : tableurs et dépôt des lots.

- `SpreadsheetReader.read(content)` : reconnaît le format **aux octets** (`.xlsx` = archive
  ZIP, sinon texte CSV séparé par virgule ou point-virgule, UTF-8 avec ou sans BOM) et rend
  le tableau (`Sheet`). Illisible, `.xls`, feuille absente → `IMPORT_FILE_INVALID` avec la
  raison ; jamais d'exception de bibliothèque brute.
- `SpreadsheetWriter` : modèle `.xlsx` (feuille de saisie, listes déroulantes, « Mode
  d'emploi ») et tableau simple (rapport d'erreurs `errors.xlsx`, T35).
- `ImportBatchRepository` : lots de la boutique ; numéro et aperçu uniques par boutique.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.application.imports.workbook import TemplateWorkbook
from app.application.ports.aggregate import UniqueKey
from app.application.shops.ports import ShopRecordRepository
from app.domain.imports.batch import ImportBatch
from app.domain.imports.columns import CellValue
from app.domain.imports.ids import ImportBatchId, ImportPreviewId
from app.domain.imports.sheet import Sheet
from app.domain.imports.values import SpreadsheetFormat

IMPORT_BATCH_NUMBER = "import_batch_number"
IMPORT_BATCH_PREVIEW = "import_batch_preview"


class SpreadsheetReader(ABC):
    @abstractmethod
    def read(self, content: bytes) -> tuple[SpreadsheetFormat, Sheet]:
        """Format reconnu et tableau lu ; `ImportFileInvalid` si le fichier est illisible."""


class SpreadsheetWriter(ABC):
    @abstractmethod
    def template(self, workbook: TemplateWorkbook) -> bytes:
        """Modèle `.xlsx` à remplir (voir `domain/imports/template.py`)."""

    @abstractmethod
    def table(
        self, title: str, header: Sequence[str], rows: Sequence[Sequence[CellValue]]
    ) -> bytes:
        """Classeur `.xlsx` d'une seule feuille : en-tête puis lignes."""


class ImportBatchRepository(ShopRecordRepository[ImportBatchId, ImportBatch]):
    def unique_keys(self) -> Sequence[UniqueKey[ImportBatch]]:
        return (
            UniqueKey(IMPORT_BATCH_NUMBER, lambda batch: str(batch.number)),
            UniqueKey(IMPORT_BATCH_PREVIEW, lambda batch: batch.preview_id.value),
        )

    @abstractmethod
    def find_by_preview(self, preview_id: ImportPreviewId) -> ImportBatch | None:
        """Lot né de cet aperçu (confirmation rejouée, IMP-09), ou `None`."""
