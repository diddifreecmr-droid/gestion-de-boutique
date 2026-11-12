"""`GET /attachments/{id}/url` — lien signé court, **après** contrôle des droits (TR-17).

Pièce d'une autre boutique ou hors de la portée de l'acteur → 404 ; permission absente ou
pièce d'identité demandée par un autre rôle que propriétaire ou vendeur → 403 (journalisé).
"""

from dataclasses import dataclass

from app.application.attachments.access import AttachmentAccess
from app.application.attachments.links import LinkSigner, SignedLink
from app.application.attachments.ports import AttachmentRepository
from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWorkFactory
from app.application.security.actor import Actor
from app.application.shops.context import actor_shop
from app.domain.attachments.attachment import Attachment
from app.domain.catalog.ids import AttachmentId


@dataclass(frozen=True, slots=True)
class IssuedLink:
    attachment: Attachment
    link: SignedLink


class IssueAttachmentLink:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        access: AttachmentAccess,
        clock: Clock,
        signer: LinkSigner,
    ) -> None:
        self._uow_factory = uow_factory
        self._access = access
        self._clock = clock
        self._signer = signer

    def execute(self, actor: Actor, attachment_id: AttachmentId) -> IssuedLink:
        with self._uow_factory(actor_shop(actor)) as uow:
            attachment = AttachmentRepository.within(uow).get(attachment_id)
            self._access.require_read(uow, actor, attachment)
        link = self._signer.sign(attachment.shop_id, attachment.id, self._clock.now())
        return IssuedLink(attachment, link)
