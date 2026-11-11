"""Secrets opaques : jetons de rafraîchissement et codes provisoires (module `secrets`).

- Rafraîchissement : 32 octets aléatoires (256 bits) en base64 URL sans remplissage, sûrs dans
  un cookie. Empreinte stockée : **SHA-256** hexadécimal. Un hachage lent est inutile ici : le
  secret a 256 bits d'entropie, aucune attaque par dictionnaire n'est possible ; l'empreinte
  évite seulement qu'une fuite de la base livre des jetons utilisables.
- Code provisoire : 6 chiffres tirés uniformément (`secrets.randbelow`).
"""

import hashlib
import secrets

from app.application.identity.ports import RefreshSecrets, TemporaryPinGenerator
from app.domain.identity.credentials import PIN_LENGTH

REFRESH_SECRET_BYTES = 32


class RandomRefreshSecrets(RefreshSecrets):
    def generate(self) -> str:
        return secrets.token_urlsafe(REFRESH_SECRET_BYTES)

    def digest(self, secret: str) -> str:
        return hashlib.sha256(secret.encode("utf-8")).hexdigest()


class RandomPinGenerator(TemporaryPinGenerator):
    def generate(self) -> str:
        return f"{secrets.randbelow(10**PIN_LENGTH):0{PIN_LENGTH}d}"
