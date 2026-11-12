"""Liens signés courts vers le contenu d'une pièce jointe (TR-17, specs § 8.2 : 60 s).

Le lien est délivré **après** contrôle des droits (`IssueAttachmentLink`) ; il porte sa date
d'expiration et une signature HMAC-SHA256 de `(boutique, pièce, expiration)`. La lecture
(`ReadAttachmentContent`) n'exige donc pas de jeton d'accès : une balise `<img>` ou un
téléchargement du navigateur l'ouvre tel quel, pendant la durée de validité seulement.

- Signature fausse, d'une autre pièce ou d'une autre boutique → `NotFound` (aucune fuite).
- Signature juste mais date dépassée (horloge `Clock`) → `LinkExpired` (410).
- La clé est dérivée du secret de l'application par la composition root ; la changer invalide
  les liens en cours (60 s au plus).
"""

import base64
import hashlib
import hmac
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.application.attachments.ports import LinkExpired
from app.application.ports.repository import not_found
from app.domain.catalog.ids import AttachmentId
from app.domain.shared.ids import ShopId

MIN_KEY_BYTES = 32
MIN_TTL = timedelta(seconds=5)
MAX_TTL = timedelta(hours=1)


@dataclass(frozen=True, slots=True)
class SignedLink:
    shop_id: ShopId
    attachment_id: AttachmentId
    expires: int
    """Expiration en secondes Unix (entier : c'est ce qui est signé)."""
    signature: str

    @property
    def expires_at(self) -> datetime:
        return datetime.fromtimestamp(self.expires, tz=UTC)


class LinkSigner:
    def __init__(self, key: bytes, ttl: timedelta) -> None:
        if len(key) < MIN_KEY_BYTES:
            msg = f"Clé de signature des liens : au moins {MIN_KEY_BYTES} octets"
            raise ValueError(msg)
        if not MIN_TTL <= ttl <= MAX_TTL:
            msg = f"Durée d'un lien signé hors bornes ({MIN_TTL} à {MAX_TTL})"
            raise ValueError(msg)
        self._key = key
        self._ttl = ttl

    @property
    def ttl(self) -> timedelta:
        return self._ttl

    def sign(self, shop_id: ShopId, attachment_id: AttachmentId, now: datetime) -> SignedLink:
        expires = int((now + self._ttl).timestamp())
        signature = self._digest(shop_id, attachment_id, expires)
        return SignedLink(shop_id, attachment_id, expires, signature)

    def verify(
        self,
        shop_id: ShopId,
        attachment_id: AttachmentId,
        expires: int,
        signature: str,
        now: datetime,
    ) -> None:
        expected = self._digest(shop_id, attachment_id, expires)
        if not hmac.compare_digest(expected.encode("ascii"), signature.encode("ascii", "replace")):
            raise not_found(attachment_id)
        if now.timestamp() > expires:
            msg = "Lien expiré : rouvrir la pièce jointe"
            raise LinkExpired(
                msg, details={"expired_at": datetime.fromtimestamp(expires, UTC).isoformat()}
            )

    def _digest(self, shop_id: ShopId, attachment_id: AttachmentId, expires: int) -> str:
        message = f"{shop_id.value}|{attachment_id.value}|{expires}".encode("ascii")
        raw = hmac.new(self._key, message, hashlib.sha256).digest()
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def derive_link_key(application_secret: bytes) -> bytes:
    """Clé propre aux liens, dérivée du secret de l'application (séparation des usages)."""
    return hmac.new(application_secret, b"attachment-links/v1", hashlib.sha256).digest()
