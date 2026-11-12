"""`POST /attachments` — envoyer une photo ou un PDF (RG-T26, TR-17, UC-CRE-07).

Ordre des contrôles : droit d'envoi (403, journalisé) → élément lié visible (404) → taille et
format reconnus aux octets (400) → écriture du fichier (503 `STORAGE_UNAVAILABLE` si le
stockage ne répond pas ; rien n'est inscrit en base) → métadonnées + journal, même transaction.

Si la transaction échoue après l'écriture du fichier, l'objet reste orphelin dans le bucket
privé : inaccessible (aucune ligne ne le cite), sans fuite ; le rejeu du même `id` le réécrit.

Idempotence (specs § 6.1) : un `id` client déjà enregistré renvoie la pièce existante
(`created=False`) après contrôle de lecture, sans réécrire le fichier.
"""

from dataclasses import dataclass
from uuid import UUID

from app.application.attachments.access import AttachmentAccess
from app.application.attachments.ports import AttachmentRepository, FileStorage
from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWorkFactory
from app.application.security.actor import Actor
from app.application.shops.context import actor_shop, performer_of
from app.domain.attachments.attachment import Attachment, AttachmentFile
from app.domain.attachments.values import AttachmentKind, OwnerType, detect_format, require_size
from app.domain.catalog.ids import AttachmentId


@dataclass(frozen=True, slots=True, kw_only=True)
class UploadCommand:
    owner_type: OwnerType
    owner_id: UUID | None
    kind: AttachmentKind
    content: bytes
    attachment_id: AttachmentId | None = None


class UploadAttachment:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        access: AttachmentAccess,
        clock: Clock,
        storage: FileStorage,
    ) -> None:
        self._uow_factory = uow_factory
        self._access = access
        self._clock = clock
        self._storage = storage

    def execute(self, actor: Actor, command: UploadCommand) -> tuple[Attachment, bool]:
        with self._uow_factory(actor_shop(actor)) as uow:
            attachments = AttachmentRepository.within(uow)
            if command.attachment_id is not None:
                existing = attachments.find(command.attachment_id)
                if existing is not None:
                    self._access.require_read(uow, actor, existing)
                    return existing, False
            self._access.require_upload(uow, actor, command.owner_type, command.owner_id)
            size = require_size(len(command.content))  # vide ou trop lourd, avant le format
            file = AttachmentFile(
                owner_type=command.owner_type,
                owner_id=command.owner_id,
                kind=command.kind,
                file_format=detect_format(command.content),
                size_bytes=size,
            )
            attachment = Attachment.upload(
                uow.shop_id,
                file,
                performer=performer_of(actor),
                now=self._clock.now(),
                attachment_id=command.attachment_id,
            )
            self._storage.put(attachment.storage_key, command.content, file.file_format)
            attachments.add(attachment)
            uow.commit()
        return attachment, True
