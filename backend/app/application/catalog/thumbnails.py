"""Vignettes de la recherche d'articles (UC-PAP-02, T30) : un lien signé court par photo.

`GET /articles?with_thumbnails=true` sert, **dans la même requête**, un lien vers la photo de
chaque article de la page ; les pièces jointes sont lues en **une** fois (`find_many`), jamais
une lecture par article, et le client n'a pas à demander `GET /attachments/{id}/url` article
par article.

Droits, **avant** toute signature (TR-17) : ceux d'une pièce rattachée à un article
(`access.RIGHTS[OwnerType.ARTICLE]`) — module `catalog` actif, permission `STOCK_READ`. Les
pièces d'article ne sont jamais personnelles ni des pièces d'identité (`require_kind_allowed`) :
ce contrôle unique vaut donc celui de `AttachmentAccess.require_read` pour chacune.

Pas de lien (vignette `None`, le client affiche les initiales) quand la photo :

- n'est pas (encore) arrivée : la fiche est enregistrée avant l'envoi de la photo, qui peut
  être en attente de réseau (le client garde la photo et réessaie, specs § 9) ;
- est rattachée à **autre chose** qu'un article (`photo_id` n'a pas de clé étrangère) : une
  pièce d'identité citée par une fiche ne doit jamais sortir par la liste des articles ;
- n'est pas une image (PDF) : une vignette est une image.
"""

from collections.abc import Mapping, Sequence
from types import MappingProxyType

from app.application.attachments.access import RIGHTS
from app.application.attachments.links import LinkSigner, SignedLink
from app.application.attachments.ports import AttachmentRepository
from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWork
from app.application.security.actor import Actor
from app.application.security.policy import Policy
from app.application.shops.modules import require_module
from app.domain.attachments.attachment import Attachment
from app.domain.attachments.values import FileFormat, OwnerType
from app.domain.catalog.article import Article
from app.domain.catalog.ids import ArticleId
from app.domain.shared.errors import ValidationFailed

IMAGE_FORMATS = frozenset({FileFormat.JPEG, FileFormat.PNG})


class ThumbnailsUnavailable(ValidationFailed):
    """Vignettes demandées sans signataire de liens branché (outils, bancs ciblés) → 400."""

    code = "THUMBNAILS_UNAVAILABLE"

    def __init__(self) -> None:
        super().__init__(
            "Les vignettes ne sont pas disponibles", details={"field": "with_thumbnails"}
        )


def is_thumbnail(attachment: Attachment) -> bool:
    file = attachment.file
    return file.owner_type is OwnerType.ARTICLE and file.file_format in IMAGE_FORMATS


class ArticleThumbnails:
    def __init__(self, policy: Policy, clock: Clock, signer: LinkSigner) -> None:
        self._policy = policy
        self._clock = clock
        self._signer = signer

    def issue(
        self, uow: UnitOfWork, actor: Actor, articles: Sequence[Article]
    ) -> Mapping[ArticleId, SignedLink | None]:
        """Lien de la photo de chaque article (`None` : pas de vignette). 403 sans le droit."""
        rights = RIGHTS[OwnerType.ARTICLE]
        require_module(uow, rights.module)
        self._policy.require(actor, rights.read)
        wanted = {a.details.photo_id for a in articles if a.details.photo_id is not None}
        found = AttachmentRepository.within(uow).find_many(wanted)
        photos = {item.id: item for item in found if is_thumbnail(item)}
        now = self._clock.now()
        links: dict[ArticleId, SignedLink | None] = {}
        for article in articles:
            photo = photos.get(article.details.photo_id) if article.details.photo_id else None
            links[article.id] = (
                None if photo is None else self._signer.sign(photo.shop_id, photo.id, now)
            )
        return MappingProxyType(links)
