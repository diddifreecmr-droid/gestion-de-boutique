"""Schémas des pièces jointes (TR-17) : métadonnées et lien signé court.

Jamais de clé de stockage, de nom de bucket ni d'adresse du service de fichiers dans une
réponse : le lien pointe vers l'API, qui relaie le contenu (docs/deploiement.md).
"""

from datetime import datetime

from pydantic import BaseModel

from app.domain.attachments.values import AttachmentKind, FileFormat, OwnerType


class AttachmentResponse(BaseModel):
    id: str
    owner_type: OwnerType
    owner_id: str | None
    kind: AttachmentKind
    mime: FileFormat
    size_bytes: int
    uploaded_at: datetime


class AttachmentLinkResponse(BaseModel):
    url: str
    """Chemin relatif à l'origine (`/api/v1/shops/…/content?expires=…&signature=…`)."""
    expires_at: datetime
    mime: FileFormat
    kind: AttachmentKind
