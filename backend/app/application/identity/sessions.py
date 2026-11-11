"""Émission des jetons d'une session : partagé par `Login` et `RefreshSession`.

Jeton de rafraîchissement (cookie httpOnly, specs § 7.2) : `<session_id>.<secret>`. Le secret
est opaque et aléatoire ; seule son empreinte est stockée (`DeviceSession.refresh_hash`).
L'identifiant de session permet de retrouver la session même quand le secret présenté est
**périmé** : c'est ainsi qu'une réutilisation est détectée et la session révoquée.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.application.identity.ports import AccessClaims, RefreshSecrets, TokenService
from app.application.identity.uow import IdentityUnitOfWork
from app.domain.identity.errors import Unauthenticated
from app.domain.identity.events import SessionId
from app.domain.identity.session import DeviceSession
from app.domain.identity.user import User
from app.domain.shared.errors import InvalidIdentifier
from app.domain.shared.ids import DeviceId, UserId

REFRESH_TOKEN_SEPARATOR = "."


@dataclass(frozen=True, slots=True)
class SessionPolicy:
    """Durées de vie (specs § 7.2 et § 15.1), fournies par la configuration."""

    access_ttl: timedelta = timedelta(minutes=15)
    refresh_ttl: timedelta = timedelta(days=30)
    """Inactivité maximale d'une session de boutique (glissante)."""
    admin_session_ttl: timedelta = timedelta(hours=8)
    """Durée absolue d'une session d'administrateur plateforme."""

    def __post_init__(self) -> None:
        for name in ("access_ttl", "refresh_ttl", "admin_session_ttl"):
            if getattr(self, name) <= timedelta(0):
                msg = f"SessionPolicy.{name} doit être strictement positive"
                raise ValueError(msg)

    def session_lifetime(self, user: User) -> timedelta:
        return self.admin_session_ttl if user.is_platform_admin else self.refresh_ttl


@dataclass(frozen=True, slots=True, kw_only=True)
class IssuedSession:
    """Résultat d'une connexion ou d'un rafraîchissement."""

    user_id: UserId
    session_id: SessionId
    access_token: str
    access_expires_at: datetime
    refresh_token: str
    refresh_expires_at: datetime
    must_change_pin: bool
    is_platform_admin: bool


def format_refresh_token(session_id: SessionId, secret: str) -> str:
    return f"{session_id}{REFRESH_TOKEN_SEPARATOR}{secret}"


def parse_refresh_token(token: str) -> tuple[SessionId, str]:
    """`(session_id, secret)` ; `Unauthenticated` si le jeton est mal formé."""
    raw_id, separator, secret = token.partition(REFRESH_TOKEN_SEPARATOR)
    if not separator or not secret:
        msg = "Jeton de rafraîchissement illisible"
        raise Unauthenticated(msg)
    try:
        return SessionId.parse(raw_id), secret
    except InvalidIdentifier as exc:
        msg = "Jeton de rafraîchissement illisible"
        raise Unauthenticated(msg) from exc


class SessionIssuer:
    """Ouvre, réutilise ou fait tourner une session et émet les deux jetons."""

    def __init__(
        self, tokens: TokenService, secrets: RefreshSecrets, policy: SessionPolicy
    ) -> None:
        self._tokens = tokens
        self._secrets = secrets
        self.policy = policy

    def open(
        self,
        uow: IdentityUnitOfWork,
        user: User,
        device_id: DeviceId,
        device_label: str,
        now: datetime,
    ) -> IssuedSession:
        """Connexion : la session active de cet appareil est réutilisée, sinon créée."""
        secret = self._secrets.generate()
        digest = self._secrets.digest(secret)
        lifetime = self.policy.session_lifetime(user)
        session = uow.sessions.active_for_device(user.id, device_id)
        if session is not None and session.is_active(now):
            session.reopen(digest, device_label, now, lifetime)
            uow.sessions.update(session)
        else:
            session = DeviceSession.open(
                user_id=user.id,
                device_id=device_id,
                device_label=device_label,
                refresh_hash=digest,
                now=now,
                lifetime=lifetime,
                sliding=not user.is_platform_admin,
            )
            uow.sessions.add(session)
        return self._issue(session, user, secret, now)

    def rotate(
        self, uow: IdentityUnitOfWork, session: DeviceSession, user: User, now: datetime
    ) -> IssuedSession:
        """Rafraîchissement : nouveau secret, l'ancien devient une réutilisation."""
        secret = self._secrets.generate()
        session.rotate(self._secrets.digest(secret), now, self.policy.session_lifetime(user))
        uow.sessions.update(session)
        return self._issue(session, user, secret, now)

    def _issue(
        self, session: DeviceSession, user: User, secret: str, now: datetime
    ) -> IssuedSession:
        access_expires_at = min(now + self.policy.access_ttl, session.expires_at)
        claims = AccessClaims(
            user_id=user.id,
            session_id=session.id,
            is_platform_admin=user.is_platform_admin,
            issued_at=now,
            expires_at=access_expires_at,
        )
        return IssuedSession(
            user_id=user.id,
            session_id=session.id,
            access_token=self._tokens.issue(claims),
            access_expires_at=access_expires_at,
            refresh_token=format_refresh_token(session.id, secret),
            refresh_expires_at=session.expires_at,
            must_change_pin=user.must_change_pin,
            is_platform_admin=user.is_platform_admin,
        )
