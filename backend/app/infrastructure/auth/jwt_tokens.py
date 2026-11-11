"""`TokenService` JWT HS256 (PyJWT), specs § 8.1.

Claims : `sub` (utilisateur), `sid` (session), `adm` (admin plateforme, booléen), `iat`, `exp`
(secondes Unix). Le rôle n'y figure **pas**. Tous les claims sont obligatoires ; seul `HS256`
est accepté (pas de `none`, pas de confusion d'algorithme).

Le secret doit compter **au moins 32 octets** (RFC 7518 § 3.2 : clé ≥ taille du condensat) ;
plus court → `ValueError` à la construction, donc au démarrage. L'expiration est contrôlée avec
le port `Clock` (et non l'horloge système) pour rester testable et cohérente avec le domaine.
"""

from datetime import UTC, datetime, timedelta

import jwt

from app.application.identity.ports import AccessClaims, TokenService
from app.application.ports.clock import Clock
from app.domain.identity.errors import Unauthenticated
from app.domain.identity.events import SessionId
from app.domain.shared.errors import InvalidIdentifier
from app.domain.shared.ids import UserId

ALGORITHM = "HS256"
MIN_SECRET_BYTES = 32
REQUIRED_CLAIMS = ("sub", "sid", "adm", "iat", "exp")
CLOCK_LEEWAY = timedelta(seconds=30)
"""Tolérance sur `iat` dans le futur (horloges de plusieurs instances légèrement décalées)."""


def require_strong_secret(secret: str) -> bytes:
    key = secret.encode("utf-8")
    if len(key) < MIN_SECRET_BYTES:
        msg = f"Le secret JWT doit compter au moins {MIN_SECRET_BYTES} octets"
        raise ValueError(msg)
    return key


def _invalid(message: str = "Jeton d'accès invalide") -> Unauthenticated:
    return Unauthenticated(message)


class JwtTokenService(TokenService):
    def __init__(self, secret: str, clock: Clock) -> None:
        self._key = require_strong_secret(secret)
        self._clock = clock

    def issue(self, claims: AccessClaims) -> str:
        payload = {
            "sub": str(claims.user_id),
            "sid": str(claims.session_id),
            "adm": claims.is_platform_admin,
            "iat": int(claims.issued_at.timestamp()),
            "exp": int(claims.expires_at.timestamp()),
        }
        return jwt.encode(payload, self._key, algorithm=ALGORITHM)

    def verify(self, token: str) -> AccessClaims:
        try:
            payload = jwt.decode(
                token,
                self._key,
                algorithms=[ALGORITHM],
                options={
                    "require": list(REQUIRED_CLAIMS),
                    "verify_exp": False,  # contrôlés ci-dessous avec le port Clock
                    "verify_iat": False,
                },
            )
        except jwt.InvalidTokenError as exc:
            raise _invalid() from exc
        issued_at, expires_at = (
            self._instant(payload["iat"]),
            self._instant(payload["exp"]),
        )
        now = self._clock.now()
        if now >= expires_at:
            msg = "Jeton d'accès expiré"
            raise _invalid(msg)
        if issued_at > now + CLOCK_LEEWAY or expires_at <= issued_at:
            raise _invalid()
        if not isinstance(payload["adm"], bool):
            raise _invalid()
        try:
            user_id = UserId.parse(str(payload["sub"]))
            session_id = SessionId.parse(str(payload["sid"]))
        except InvalidIdentifier as exc:
            raise _invalid() from exc
        return AccessClaims(
            user_id=user_id,
            session_id=session_id,
            is_platform_admin=payload["adm"],
            issued_at=issued_at,
            expires_at=expires_at,
        )

    @staticmethod
    def _instant(value: object) -> datetime:
        if isinstance(value, bool) or not isinstance(value, int):
            raise _invalid()
        return datetime.fromtimestamp(value, tz=UTC)
