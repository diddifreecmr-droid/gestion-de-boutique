"""Agrégat `Attachment` : fichier rattaché à un élément de la boutique (CDC § 20.5, TR-17).

- Le **contenu** n'est pas dans l'agrégat : il est confié au port `FileStorage` sous une clé
  calculée ici (`storage_key`), jamais à partir d'un nom fourni par le client (aucun chemin
  arbitraire, aucune collision entre boutiques).
- `owner_id` : élément lié. Obligatoire pour un client ou une créance (données personnelles,
  la visibilité en hérite) ; facultatif ailleurs, la photo étant prise avant l'enregistrement
  de l'élément (dépense, achat, ajustement, article) et son identifiant gardé par celui-ci.
- `uploaded_by` : l'auteur de l'envoi garde l'accès à sa pièce (portée « Siens »).
- Aucune modification ni suppression (RG-T02) : une pièce remplacée reste au dossier.
"""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from app.domain.attachments.events import AttachmentUploaded
from app.domain.attachments.values import (
    AttachmentKind,
    FileFormat,
    OwnerType,
    require_kind_allowed,
    require_size,
)
from app.domain.audit.values import EntityRef, Performer
from app.domain.catalog.ids import AttachmentId
from app.domain.shared.business_day import require_aware
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.events import EventCollector
from app.domain.shared.ids import ShopId, UserId

KIND_LABELS = {
    AttachmentKind.ID_DOCUMENT: "Pièce d'identité",
    AttachmentKind.CONTRACT: "Contrat",
    AttachmentKind.DEBT_ACKNOWLEDGEMENT: "Reconnaissance de dette",
    AttachmentKind.INVOICE: "Facture",
    AttachmentKind.RECEIPT: "Justificatif",
    AttachmentKind.PHOTO: "Photo",
    AttachmentKind.OTHER: "Autre",
}


@dataclass(frozen=True, slots=True, kw_only=True)
class AttachmentFile:
    """Ce que l'envoi déclare et ce que le serveur a reconnu (format, taille)."""

    owner_type: OwnerType
    owner_id: UUID | None
    kind: AttachmentKind
    file_format: FileFormat
    size_bytes: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "owner_type", OwnerType(self.owner_type))
        object.__setattr__(self, "kind", AttachmentKind(self.kind))
        object.__setattr__(self, "file_format", FileFormat(self.file_format))
        require_size(self.size_bytes)
        if self.owner_id is not None and not isinstance(self.owner_id, UUID):
            msg = "AttachmentFile.owner_id doit être un UUID"
            raise TypeError(msg)
        if self.owner_type.is_personal and self.owner_id is None:
            msg = "Élément lié obligatoire pour un client ou une créance"
            raise ValidationFailed(msg, details={"field": "owner_id"})
        require_kind_allowed(self.kind, self.owner_type)


@dataclass(eq=False, kw_only=True)
class Attachment:
    id: AttachmentId
    shop_id: ShopId
    file: AttachmentFile
    uploaded_by: UserId
    uploaded_at: datetime
    version: int = 0
    events: EventCollector = field(default_factory=EventCollector, repr=False)

    def __post_init__(self) -> None:
        self.uploaded_at = require_aware(self.uploaded_at)
        if not isinstance(self.file, AttachmentFile):
            msg = "Attachment.file doit être un AttachmentFile"
            raise TypeError(msg)

    @property
    def storage_key(self) -> str:
        """Clé de l'objet stocké : boutique, identifiant et extension, rien du client."""
        extension = self.file.file_format.extension
        return f"shops/{self.shop_id.value}/attachments/{self.id.value}.{extension}"

    @property
    def is_id_document(self) -> bool:
        return self.file.kind is AttachmentKind.ID_DOCUMENT

    @property
    def entity(self) -> EntityRef:
        return EntityRef("attachment", self.id.value, KIND_LABELS[self.file.kind])

    @classmethod
    def upload(
        cls,
        shop_id: ShopId,
        file: AttachmentFile,
        *,
        performer: Performer,
        now: datetime,
        attachment_id: AttachmentId | None = None,
    ) -> "Attachment":
        attachment = cls(
            id=attachment_id or AttachmentId.new(),
            shop_id=shop_id,
            file=file,
            uploaded_by=performer.user_id,
            uploaded_at=now,
        )
        owner = file.owner_type.value
        attachment.events.record(
            AttachmentUploaded(
                shop_id=shop_id,
                occurred_at=now,
                performer=performer,
                entity=attachment.entity,
                summary=f"Pièce jointe ajoutée ({KIND_LABELS[file.kind]}, {owner})",
            )
        )
        return attachment
