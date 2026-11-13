"""Dépôt mémoire des pièces jointes (métadonnées ; contenu dans `FileStorage`)."""

import copy
from collections.abc import Collection
from typing import cast

from app.application.attachments.ports import AttachmentRepository
from app.domain.attachments.attachment import Attachment
from app.domain.catalog.ids import AttachmentId
from app.infrastructure.persistence.memory.repository import MemoryRepository


class MemoryAttachmentRepository(MemoryRepository[AttachmentId, Attachment], AttachmentRepository):
    table = "attachments"

    def find_many(self, ids: Collection[AttachmentId]) -> list[Attachment]:
        wanted = set(ids)
        if not wanted:
            return []
        # Les lignes de cette table ne sont construites que par `_row` à partir d'une pièce.
        rows = self._transaction.rows(self.table)
        found = [cast(Attachment, copy.deepcopy(row.payload)) for row in rows]
        return self._tracked([item for item in found if item.id in wanted])


MEMORY_ATTACHMENT_REPOSITORIES = (MemoryAttachmentRepository,)
