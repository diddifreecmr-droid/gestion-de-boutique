"""`GET /attachments/{id}/content?expires=&signature=` — contenu relayé par l'API (TR-17).

Aucun jeton d'accès : le lien signé **est** l'autorisation, délivrée par `IssueAttachmentLink`
après contrôle des droits, valable `ttl` (60 s). Le stockage n'est jamais exposé au navigateur :
l'API lit l'objet sur le réseau interne et le renvoie (specs § 8.4, docs/deploiement.md).
"""

from dataclasses import dataclass

from app.application.attachments.links import LinkSigner
from app.application.attachments.ports import AttachmentRepository, FileStorage
from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWorkFactory
from app.domain.attachments.attachment import Attachment
from app.domain.catalog.ids import AttachmentId
from app.domain.shared.ids import ShopId


@dataclass(frozen=True, slots=True)
class AttachmentContent:
    attachment: Attachment
    content: bytes


class ReadAttachmentContent:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        clock: Clock,
        signer: LinkSigner,
        storage: FileStorage,
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._signer = signer
        self._storage = storage

    def execute(
        self, shop_id: ShopId, attachment_id: AttachmentId, expires: int, signature: str
    ) -> AttachmentContent:
        self._signer.verify(shop_id, attachment_id, expires, signature, self._clock.now())
        with self._uow_factory(shop_id) as uow:
            attachment = AttachmentRepository.within(uow).get(attachment_id)
        return AttachmentContent(attachment, self._storage.get(attachment.storage_key))
