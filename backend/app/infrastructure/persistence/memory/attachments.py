"""Dépôt mémoire des pièces jointes (métadonnées ; contenu dans `FileStorage`)."""

from app.application.attachments.ports import AttachmentRepository
from app.domain.attachments.attachment import Attachment
from app.domain.catalog.ids import AttachmentId
from app.infrastructure.persistence.memory.repository import MemoryRepository


class MemoryAttachmentRepository(MemoryRepository[AttachmentId, Attachment], AttachmentRepository):
    table = "attachments"


MEMORY_ATTACHMENT_REPOSITORIES = (MemoryAttachmentRepository,)
