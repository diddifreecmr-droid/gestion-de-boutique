"""Fichiers d'aperçu gardés dans `FileStorage` (UC-IMP-02, IMP-03, IMP-09, SEC-I3-01).

L'aperçu **n'écrit rien en base** : le fichier déposé et ce qui le décrit (modèle, format, auteur,
heure du dépôt) forment un seul objet du stockage, sous une clé calculée par le serveur :

    shops/<boutique>/imports/<preview_id>.bin
    = PREVIEW_MAGIC + description JSON sur une ligne + "\n" + octets du fichier

`load` (confirmation, T33 ; rapport d'erreurs, T35) relit l'aperçu :

- clé absente (identifiant inventé, autre boutique) ou dépôt d'un autre utilisateur → 404 ;
- plus de 30 minutes après le dépôt → 410 `IMPORT_PREVIEW_EXPIRED` ;
- objet présent mais mal formé → `RuntimeError` (incohérence du stockage, jamais masquée).

Les objets d'aperçu ne sont pas effacés (le port n'a pas de suppression) : le fichier d'un lot
confirmé reste sa source (`ImportBatch.source_file_key`).
"""

import json
import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.application.attachments.ports import FileStorage, MissingFile
from app.application.ports.repository import not_found
from app.domain.imports.errors import ImportPreviewExpired
from app.domain.imports.ids import ImportPreviewId
from app.domain.imports.values import PREVIEW_TTL, ImportKind, SpreadsheetFormat
from app.domain.shared.business_day import require_aware
from app.domain.shared.ids import ShopId, UserId, build_uuid7

PREVIEW_MAGIC = b"GB-IMPORT-PREVIEW/1\n"
PREVIEW_MEDIA_TYPE = "application/octet-stream"
FILE_NAME_MAX = 120


def new_preview_id(now: datetime) -> ImportPreviewId:
    """UUIDv7 horodaté à l'heure du serveur (l'horloge injectée), partie aléatoire sûre."""
    timestamp_ms = int(require_aware(now).timestamp() * 1000)
    return ImportPreviewId(build_uuid7(timestamp_ms, secrets.randbits(74)))


def preview_key(shop_id: ShopId, preview_id: ImportPreviewId) -> str:
    return f"shops/{shop_id.value}/imports/{preview_id.value}.bin"


@dataclass(frozen=True, slots=True, kw_only=True)
class StoredPreview:
    preview_id: ImportPreviewId
    kind: ImportKind
    file_format: SpreadsheetFormat
    uploaded_by: UserId
    uploaded_at: datetime
    file_name: str | None
    content: bytes

    @property
    def expires_at(self) -> datetime:
        return self.uploaded_at + PREVIEW_TTL

    def encode(self) -> bytes:
        header = {
            "kind": self.kind.value,
            "format": self.file_format.value,
            "uploaded_by": str(self.uploaded_by.value),
            "uploaded_at": require_aware(self.uploaded_at).isoformat(),
            "file_name": None if self.file_name is None else self.file_name[:FILE_NAME_MAX],
        }
        line = json.dumps(header, ensure_ascii=True, separators=(",", ":")).encode("ascii")
        return PREVIEW_MAGIC + line + b"\n" + self.content

    @classmethod
    def decode(cls, preview_id: ImportPreviewId, stored: bytes) -> "StoredPreview":
        if not stored.startswith(PREVIEW_MAGIC):
            msg = f"Aperçu d'import {preview_id} : objet du stockage mal formé"
            raise RuntimeError(msg)
        line, separator, content = stored[len(PREVIEW_MAGIC) :].partition(b"\n")
        try:
            header: Any = json.loads(line) if separator else None
            return cls(
                preview_id=preview_id,
                kind=ImportKind(header["kind"]),
                file_format=SpreadsheetFormat(header["format"]),
                uploaded_by=UserId.parse(header["uploaded_by"]),
                uploaded_at=require_aware(datetime.fromisoformat(header["uploaded_at"])),
                file_name=header["file_name"],
                content=content,
            )
        except (TypeError, KeyError, ValueError) as exc:
            msg = f"Aperçu d'import {preview_id} : description illisible"
            raise RuntimeError(msg) from exc


class PreviewFiles:
    def __init__(self, storage: FileStorage) -> None:
        self._storage = storage

    def keep(self, shop_id: ShopId, preview: StoredPreview) -> str:
        """Écrit l'aperçu ; renvoie sa clé (`StorageUnavailable` → 503 si panne)."""
        key = preview_key(shop_id, preview.preview_id)
        self._storage.put(key, preview.encode(), PREVIEW_MEDIA_TYPE)
        return key

    def load(
        self, shop_id: ShopId, preview_id: ImportPreviewId, *, user_id: UserId, now: datetime
    ) -> StoredPreview:
        try:
            stored = self._storage.get(preview_key(shop_id, preview_id))
        except MissingFile as exc:  # identifiant inconnu de cette boutique : 404, sans fuite
            raise not_found(preview_id) from exc
        preview = StoredPreview.decode(preview_id, stored)
        if preview.uploaded_by != user_id:
            raise not_found(preview_id)
        if require_aware(now) > preview.expires_at:
            raise ImportPreviewExpired(str(preview_id))
        return preview
