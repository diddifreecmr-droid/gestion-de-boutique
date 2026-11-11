"""Rafraîchir la session d'un appareil par rotation (specs § 7.2, § 8.1, recette SEC-R03/R05).

- jeton illisible, session inconnue ou d'un autre appareil, session expirée → `Unauthenticated` ;
- session révoquée → `SessionRevoked` ;
- secret périmé (jeton déjà tourné, présenté à nouveau) → la session est **révoquée et la
  révocation validée**, puis `SessionRevoked` : le voleur comme la victime doivent se
  reconnecter ; les autres appareils ne sont pas touchés ;
- compte désactivé (RG-D06) ou sans rattachement utilisable (T10) → `AccountDisabled` ;
- sinon : nouveau secret, ancien invalidé, nouveau jeton d'accès. Un compte bloqué garde ses
  sessions ouvertes (le blocage vise la devinette du code, pas l'appareil déjà connecté).
"""

from app.application.identity.ports import MembershipDirectory, RefreshSecrets
from app.application.identity.reachability import require_reachable
from app.application.identity.sessions import IssuedSession, SessionIssuer, parse_refresh_token
from app.application.identity.uow import IdentityUnitOfWorkFactory
from app.application.ports.clock import Clock
from app.domain.identity.errors import SessionRevoked, Unauthenticated
from app.domain.identity.events import RevocationReason
from app.domain.shared.ids import DeviceId


class RefreshSession:
    def __init__(
        self,
        uow_factory: IdentityUnitOfWorkFactory,
        secrets: RefreshSecrets,
        issuer: SessionIssuer,
        clock: Clock,
        memberships: MembershipDirectory,
    ) -> None:
        self._uow_factory = uow_factory
        self._secrets = secrets
        self._issuer = issuer
        self._clock = clock
        self._memberships = memberships

    def execute(self, refresh_token: str, device_id: DeviceId) -> IssuedSession:
        now = self._clock.now()
        session_id, secret = parse_refresh_token(refresh_token)
        with self._uow_factory() as uow:
            session = uow.sessions.find(session_id)
            if session is None or session.device_id != device_id:
                msg = "Session inconnue sur cet appareil"
                raise Unauthenticated(msg)
            if session.revoked:
                raise SessionRevoked
            if not session.is_active(now):
                msg = "Session expirée : reconnectez-vous"
                raise Unauthenticated(msg)
            if not session.matches(self._secrets.digest(secret)):
                session.revoke(now, RevocationReason.REFRESH_REUSE)
                uow.sessions.update(session)
                uow.commit()
                raise SessionRevoked
            user = uow.users.get(session.user_id)
            user.ensure_active()
            require_reachable(self._memberships, user)
            issued = self._issuer.rotate(uow, session, user, now)
            uow.commit()
        return issued
