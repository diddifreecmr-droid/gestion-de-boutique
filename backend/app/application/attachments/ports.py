"""Ports des pièces jointes : dépôt des métadonnées et stockage objet `FileStorage` (D16).

`FileStorage` cache le service de fichiers (Silo/MinIO, tout S3 compatible, mémoire pour les
tests). Contrat (vérifié par `tests/contracts/test_file_storage_contract.py`) :

- `put(key, content, file_format)` écrit l'objet (réécrire la même clé le remplace) ;
- `get(key)` relit exactement les octets écrits ; clé absente → `MissingFile` (erreur
  d'intégrité : la base cite un fichier que le stockage n'a pas, réponse 500) ;
- service injoignable ou en erreur → `StorageUnavailable` (503 `STORAGE_UNAVAILABLE`, le
  client garde la photo et réessaie, specs § 9). Rien n'est jamais avalé.
"""

from abc import ABC, abstractmethod
from collections.abc import Collection

from app.application.shops.ports import ShopRecordRepository
from app.domain.attachments.attachment import Attachment
from app.domain.attachments.values import FileFormat
from app.domain.catalog.ids import AttachmentId
from app.domain.shared.errors import DomainError


class StorageUnavailable(DomainError):
    """Stockage de fichiers injoignable ou en erreur (→ HTTP 503)."""

    code = "STORAGE_UNAVAILABLE"


class LinkExpired(DomainError):
    """Lien signé dépassé : en redemander un (→ HTTP 410)."""

    code = "LINK_EXPIRED"


class MissingFile(RuntimeError):
    """Objet absent du stockage alors que la base le cite : incohérence, jamais masquée."""


class AttachmentRepository(ShopRecordRepository[AttachmentId, Attachment]):
    """Métadonnées des pièces jointes de la boutique (le contenu est dans `FileStorage`)."""

    @abstractmethod
    def find_many(self, ids: Collection[AttachmentId]) -> list[Attachment]:
        """Pièces **de la boutique** parmi `ids`, en **une** lecture (vignettes, T30).

        Un identifiant absent ou d'une autre boutique est simplement omis (aucune fuite) ;
        ordre non garanti ; `ids` vide → liste vide sans lecture.
        """


class FileStorage(ABC):
    """Stockage objet privé ; les clés viennent de `Attachment.storage_key`."""

    @abstractmethod
    def put(self, key: str, content: bytes, file_format: FileFormat) -> None:
        """Écrit l'objet ; `StorageUnavailable` si le service ne répond pas."""

    @abstractmethod
    def get(self, key: str) -> bytes:
        """Octets de l'objet ; `MissingFile` s'il manque, `StorageUnavailable` si panne."""
