"""`POST /imports` — « Importer les lignes valides » d'un aperçu (UC-IMP-02 étape 4, T33).

Ordre : aperçu de l'acteur (404 inconnu ou d'un autre, SEC-I3-01) → lot déjà né de cet aperçu
→ **le même lot** (`created=False`, IMP-09 : confirmation rejouée, même au-delà des 30 minutes)
→ aperçu de moins de 30 minutes (410 `IMPORT_PREVIEW_EXPIRED`) → modules et droit du modèle
(403) → relecture du fichier et **nouveau** contrôle des lignes dans la transaction (la boutique
a pu changer depuis l'aperçu) → aucune ligne valide : 422, rien d'écrit → numéro `IMP-…`,
écriture des lignes valides par le modèle (`apply`), enregistrement du lot et de ses lignes
refusées (`ImportProblemLog` : rapport `errors.xlsx`, T35).

**Une seule transaction** : tout le lot est écrit, ou rien (une erreur d'écriture annule tout).
Le journal reçoit « Importer » (`IMP-…`) et la création de chaque élément, dans la même
transaction. Deux confirmations simultanées du même aperçu : la seconde échoue sur l'unicité
de l'aperçu (409), rien n'est écrit deux fois.
"""

from dataclasses import dataclass

from app.application.imports.access import ImportAccess, shop_profile
from app.application.imports.models import ImportRun
from app.application.imports.ports import (
    ImportBatchRepository,
    ImportProblemLog,
    SpreadsheetReader,
)
from app.application.imports.previews import PreviewFiles, preview_key
from app.application.ports.clock import Clock
from app.application.ports.repository import not_found
from app.application.ports.uow import UnitOfWorkFactory
from app.application.security.actor import Actor
from app.application.shops.context import actor_shop, performer_of
from app.domain.imports.batch import ImportBatch, ImportCounts
from app.domain.imports.ids import ImportBatchId, ImportPreviewId
from app.domain.imports.sheet import read_rows
from app.domain.shared.doc_number import DocType
from app.domain.shared.errors import ValidationFailed

NOTHING_TO_IMPORT = "Aucune ligne valide à importer : corrigez le fichier et recommencez"


@dataclass(frozen=True, slots=True, kw_only=True)
class ConfirmCommand:
    preview_id: ImportPreviewId


class ConfirmImport:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        access: ImportAccess,
        clock: Clock,
        reader: SpreadsheetReader,
        previews: PreviewFiles,
    ) -> None:
        self._uow_factory = uow_factory
        self._access = access
        self._clock = clock
        self._reader = reader
        self._previews = previews

    def execute(self, actor: Actor, command: ConfirmCommand) -> tuple[ImportBatch, bool]:
        shop_id, now = actor_shop(actor), self._clock.now()
        with self._uow_factory(shop_id) as uow:
            batches = ImportBatchRepository.within(uow)
            existing = batches.find_by_preview(command.preview_id)
            if existing is not None:
                if existing.imported_by != actor.user_id:
                    raise not_found(command.preview_id)
                self._access.require(uow, actor, existing.kind)
                return existing, False
            preview = self._previews.load(
                shop_id, command.preview_id, user_id=actor.user_id, now=now
            )
            model = self._access.require(uow, actor, preview.kind)
            _, sheet = self._reader.read(preview.content)
            read = read_rows(model.template(shop_profile(uow)).columns, sheet)
            check = model.check(uow, actor, read.valid)
            accepted = set(check.accepted)
            rows = [row for row in read.valid if row.line in accepted]
            if not rows:
                details = {"field": "preview_id", "rows_read": read.rows_read}
                raise ValidationFailed(NOTHING_TO_IMPORT, details=details)
            run = ImportRun(
                batch_id=ImportBatchId.new(),
                number=uow.numbering.next(DocType.IMPORT),
                performer=performer_of(actor),
                now=now,
                today=self._clock.today(),
            )
            items = model.apply(uow, actor, rows, run)
            counts = ImportCounts(
                rows_read=read.rows_read,
                rows_imported=len(rows),
                rows_ignored=read.rows_read - len(rows),
            )
            batch = ImportBatch.record(
                shop_id,
                run.number,
                model.kind,
                preview_id=command.preview_id,
                source_file_key=preview_key(shop_id, command.preview_id),
                counts=counts,
                items=items,
                performer=run.performer,
                now=now,
                batch_id=run.batch_id,
            )
            batches.add(batch)
            ImportProblemLog.within(uow).append(batch, (*read.errors, *check.refused))
            uow.commit()
        return batch, True
