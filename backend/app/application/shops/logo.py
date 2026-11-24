"""Logo de la boutique (décision client 2026-11-24, specs § 15.1).

Le gérant envoie l'image par `POST /attachments` (élément lié `shop`, droit `SETTINGS_MANAGE`)
puis la désigne dans les réglages (`logo_attachment_id`, `null` pour la retirer). Ici :

- `require_logo` : la pièce désignée existe **dans cette boutique** (404 sinon, aucune fuite),
  est rattachée à la boutique et est une image JPG ou PNG (400 sinon) ;
- `LogoLinks` : lien signé court vers le logo, remis à tout membre avec le profil et, si
  « afficher le logo » est coché, avec le reçu (la lecture du profil vaut droit de le voir).
"""

from app.application.attachments.links import LinkSigner, SignedLink
from app.application.attachments.ports import AttachmentRepository
from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWork
from app.domain.attachments.values import IMAGE_FORMATS, OwnerType
from app.domain.catalog.ids import AttachmentId
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.ids import ShopId
from app.domain.shops.settings import SettingsValues


def require_logo(uow: UnitOfWork, attachment_id: AttachmentId) -> None:
    """Pièce de la boutique, rattachée à la boutique, JPG ou PNG ; 404 puis 400."""
    file = AttachmentRepository.within(uow).get(attachment_id).file
    if file.owner_type is not OwnerType.SHOP or file.file_format not in IMAGE_FORMATS:
        msg = "Le logo est une photo JPG ou PNG envoyée pour la boutique"
        raise ValidationFailed(msg, details={"field": "logo_attachment_id"})


class LogoLinks:
    def __init__(self, signer: LinkSigner, clock: Clock) -> None:
        self._signer = signer
        self._clock = clock

    def link(self, shop_id: ShopId, values: SettingsValues) -> SignedLink | None:
        """Lien signé du logo, ou `None` sans logo (le frontend montre le logo générique)."""
        logo = values.logo_attachment_id
        return None if logo is None else self._signer.sign(shop_id, logo, self._clock.now())


def logo_links(signer: LinkSigner | None, clock: Clock) -> LogoLinks | None:
    """Sans signataire (bancs ciblés, outils) : pas de lien de logo."""
    return None if signer is None else LogoLinks(signer, clock)
