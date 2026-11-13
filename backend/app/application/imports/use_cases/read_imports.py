"""Lots d'import : liste, détail, rapport des lignes refusées (UC-IMP-02 étape 5, T35).

- `GET /imports` : lots des modèles que l'acteur importe (`ImportAccess.readable`, M3-03 :
  le comptable ne voit ni clients ni créances), le plus récent d'abord ; aucun modèle → 403.
- `GET /imports/{id}` : modèle, date, auteur (nom du compte), lignes lues / importées /
  ignorées, éléments créés, statut, dernier jour d'annulation ; lot d'un modèle non lisible ou
  d'une autre boutique → 404.
- `GET /imports/{id}/errors.xlsx` : une ligne par problème — « Ligne », « Colonne »,
  « Problème » (IMP-10), lu dans `ImportProblemLog` (posé à la confirmation, T35).

Lecture seule : rien n'est écrit, rien n'est journalisé.
"""

from dataclasses import dataclass

from app.application.identity.uow import IdentityUnitOfWorkFactory
from app.application.imports.access import ImportAccess
from app.application.imports.ports import ImportBatchRepository, ImportProblemLog, SpreadsheetWriter
from app.application.ports.repository import not_found
from app.application.ports.uow import UnitOfWork, UnitOfWorkFactory
from app.application.security.actor import Actor
from app.application.shops.context import actor_shop
from app.domain.imports.batch import ImportBatch
from app.domain.imports.ids import ImportBatchId
from app.domain.imports.values import SpreadsheetFormat

ERRORS_HEADER = ("Ligne", "Colonne", "Problème")


@dataclass(frozen=True, slots=True, kw_only=True)
class ImportBatchView:
    batch: ImportBatch
    author_name: str
    problems_total: int


@dataclass(frozen=True, slots=True)
class ErrorsFile:
    number: str
    content: bytes

    @property
    def file_name(self) -> str:
        return f"erreurs-{self.number}.xlsx"

    @property
    def media_type(self) -> str:
        return SpreadsheetFormat.XLSX.value


class ReadImports:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        platform: IdentityUnitOfWorkFactory,
        access: ImportAccess,
        writer: SpreadsheetWriter,
    ) -> None:
        self._uow_factory = uow_factory
        self._platform = platform
        self._access = access
        self._writer = writer

    def list(self, actor: Actor) -> list[ImportBatch]:
        kinds = self._access.readable(actor)
        with self._uow_factory(actor_shop(actor)) as uow:
            batches = ImportBatchRepository.within(uow).list_all()
        return [batch for batch in batches if batch.kind in kinds]

    def get(self, actor: Actor, batch_id: ImportBatchId) -> ImportBatchView:
        with self._uow_factory(actor_shop(actor)) as uow:
            batch = self._readable(uow, actor, batch_id)
            problems = len(ImportProblemLog.within(uow).for_batch(batch.id))
        with self._platform() as platform:
            author = platform.users.get(batch.imported_by).name
        return ImportBatchView(batch=batch, author_name=author, problems_total=problems)

    def errors(self, actor: Actor, batch_id: ImportBatchId) -> ErrorsFile:
        with self._uow_factory(actor_shop(actor)) as uow:
            batch = self._readable(uow, actor, batch_id)
            problems = ImportProblemLog.within(uow).for_batch(batch.id)
        rows = [(p.line, p.column or "", p.message) for p in problems]
        title = f"Erreurs {batch.number}"
        return ErrorsFile(str(batch.number), self._writer.table(title, ERRORS_HEADER, rows))

    def _readable(self, uow: UnitOfWork, actor: Actor, batch_id: ImportBatchId) -> ImportBatch:
        kinds = self._access.readable(actor)
        batch = ImportBatchRepository.within(uow).get(batch_id)
        if batch.kind not in kinds:
            raise not_found(batch_id)
        return batch
