"""`POST /imports/preview` — aperçu ligne par ligne, **sans écriture en base** (UC-IMP-02).

Ordre des contrôles : modèle (404) → modules et droit du modèle (403) → taille du fichier
(400 `IMPORT_FILE_INVALID`) → lecture du tableur (400) → en-tête et nombre de lignes (400,
422 `IMPORT_TOO_MANY_ROWS`) → nettoyage des cellules et verdict du modèle (erreurs de ligne,
jamais d'exception) → fichier gardé dans le stockage (503 si panne) sous un `preview_id`
valable 30 minutes, que la confirmation reprend (T33).

L'unité de travail ne sert qu'à lire (profil, lieux, doublons) : elle n'est jamais validée.
"""

from dataclasses import dataclass
from datetime import datetime

from app.application.imports.access import ImportAccess, shop_profile
from app.application.imports.ports import SpreadsheetReader
from app.application.imports.previews import PreviewFiles, StoredPreview, new_preview_id
from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWorkFactory
from app.application.security.actor import Actor
from app.application.shops.context import actor_shop
from app.domain.imports.errors import ImportFileInvalid
from app.domain.imports.ids import ImportPreviewId
from app.domain.imports.problems import RowError
from app.domain.imports.sheet import read_rows
from app.domain.imports.values import MAX_FILE_BYTES, ImportKind

LISTED_PROBLEMS_MAX = 1_000
"""Problèmes détaillés dans la réponse ; au-delà, seul leur nombre est donné."""


@dataclass(frozen=True, slots=True, kw_only=True)
class PreviewCommand:
    kind: str
    content: bytes
    file_name: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class ImportPreview:
    preview_id: ImportPreviewId
    kind: ImportKind
    expires_at: datetime
    rows_read: int
    rows_valid: int
    problems: tuple[RowError, ...]
    problems_total: int
    notes: tuple[str, ...]

    @property
    def rows_ignored(self) -> int:
        return self.rows_read - self.rows_valid


def _require_size(content: bytes) -> None:
    if not content:
        reason = "le fichier est vide"
        raise ImportFileInvalid(reason)
    if len(content) > MAX_FILE_BYTES:
        reason = "fichier trop lourd (5 Mo au plus)"
        raise ImportFileInvalid(reason)


class PreviewImport:
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

    def execute(self, actor: Actor, command: PreviewCommand) -> ImportPreview:
        shop_id = actor_shop(actor)
        with self._uow_factory(shop_id) as uow:
            model = self._access.require(uow, actor, command.kind)
            _require_size(command.content)
            file_format, sheet = self._reader.read(command.content)
            spec = model.template(shop_profile(uow))
            read = read_rows(spec.columns, sheet)
            check = model.check(uow, actor, read.valid)
        judged = set(check.accepted) | {error.line for error in check.refused}
        if judged != {row.line for row in read.valid}:
            msg = f"Le modèle {model.kind} n'a pas jugé exactement les lignes valides reçues"
            raise RuntimeError(msg)
        now = self._clock.now()
        stored = StoredPreview(
            preview_id=new_preview_id(now),
            kind=model.kind,
            file_format=file_format,
            uploaded_by=actor.user_id,
            uploaded_at=now,
            file_name=command.file_name,
            content=command.content,
        )
        self._previews.keep(shop_id, stored)
        problems = tuple(sorted((*read.errors, *check.refused), key=lambda e: e.sort_key))
        return ImportPreview(
            preview_id=stored.preview_id,
            kind=model.kind,
            expires_at=stored.expires_at,
            rows_read=read.rows_read,
            rows_valid=len(check.accepted),
            problems=problems[:LISTED_PROBLEMS_MAX],
            problems_total=len(problems),
            notes=check.notes,
        )
