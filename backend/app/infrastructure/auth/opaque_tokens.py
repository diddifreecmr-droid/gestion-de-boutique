"""Secrets opaques : jetons de rafraîchissement et codes provisoires (module `secrets`).

- Rafraîchissement : 32 octets aléatoires (256 bits) en base64 URL sans remplissage, sûrs dans
  un cookie. Empreinte stockée : **SHA-256** hexadécimal. Un hachage lent est inutile ici : le
  secret a 256 bits d'entropie, aucune attaque par dictionnaire n'est possible ; l'empreinte
  évite seulement qu'une fuite de la base livre des jetons utilisables.
- Successeur à la rotation : HMAC-SHA-256 du secret présenté sous une clé serveur (256 bits,
  base64 URL). Déterministe (rejeu toléré, specs § 8.1) ; la clé ne quitte jamais le serveur :
  ni le jeton volé ni la base seule ne permettent de calculer le jeton suivant.
- Code provisoire : 6 chiffres tirés uniformément (`secrets.randbelow`).
"""

import base64
import hashlib
import hmac
import secrets

from app.application.identity.ports import RefreshSecrets, TemporaryPinGenerator
from app.domain.identity.credentials import PIN_LENGTH

REFRESH_SECRET_BYTES = 32
ROTATION_KEY_MIN_BYTES = 32
ROTATION_KEY_LABEL = b"boutique/refresh-rotation/v1"
"""Séparation de domaine : la clé de rotation est dérivée du secret JWT, jamais égale à lui."""


def rotation_key_from(server_secret: str) -> bytes:
    """Clé de rotation dérivée (HMAC) d'un secret serveur d'au moins 32 octets."""
    raw = server_secret.encode("utf-8")
    if len(raw) < ROTATION_KEY_MIN_BYTES:
        msg = f"Secret serveur trop court pour la rotation : {ROTATION_KEY_MIN_BYTES} octets exigés"
        raise ValueError(msg)
    return hmac.new(raw, ROTATION_KEY_LABEL, hashlib.sha256).digest()


class RandomRefreshSecrets(RefreshSecrets):
    def __init__(self, rotation_key: bytes) -> None:
        if len(rotation_key) < ROTATION_KEY_MIN_BYTES:
            msg = f"Clé de rotation trop courte : {ROTATION_KEY_MIN_BYTES} octets exigés"
            raise ValueError(msg)
        self._rotation_key = rotation_key

    def generate(self) -> str:
        return secrets.token_urlsafe(REFRESH_SECRET_BYTES)

    def digest(self, secret: str) -> str:
        return hashlib.sha256(secret.encode("utf-8")).hexdigest()

    def successor(self, secret: str) -> str:
        mac = hmac.new(self._rotation_key, secret.encode("utf-8"), hashlib.sha256).digest()
        return base64.urlsafe_b64encode(mac).rstrip(b"=").decode("ascii")


class RandomPinGenerator(TemporaryPinGenerator):
    def generate(self) -> str:
        return f"{secrets.randbelow(10**PIN_LENGTH):0{PIN_LENGTH}d}"
