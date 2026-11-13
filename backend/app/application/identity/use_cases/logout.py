"""Se déconnecter de cet appareil (UC-SOC-02 étape 4 : « déconnexion volontaire »).

Le jeton de rafraîchissement (cookie) désigne la session. Elle est révoquée avec le motif
`LOGOUT` si son secret est le bon (ou le jeton tout juste remplacé, rejouable pendant la fenêtre
de grâce de specs § 8.1), `REFRESH_REUSE` s'il est périmé (un jeton tourné présenté à nouveau
hors de cette fenêtre reste suspect). Une session déjà révoquée : rien à faire, la
déconnexion est acquise.
Session inconnue ou d'un autre appareil → `Unauthenticated`.
"""

from app.application.identity.ports import RefreshSecrets
from app.application.identity.sessions import parse_refresh_token
from app.application.identity.uow import IdentityUnitOfWorkFactory
from app.application.ports.clock import Clock
from app.domain.identity.errors import Unauthenticated
from app.domain.identity.events import RevocationReason
from app.domain.identity.refresh_rotation import RefreshVerdict
from app.domain.shared.ids import DeviceId


class Logout:
    def __init__(
        self, uow_factory: IdentityUnitOfWorkFactory, secrets: RefreshSecrets, clock: Clock
    ) -> None:
        self._uow_factory = uow_factory
        self._secrets = secrets
        self._clock = clock

    def execute(self, refresh_token: str, device_id: DeviceId) -> None:
        now = self._clock.now()
        session_id, secret = parse_refresh_token(refresh_token)
        with self._uow_factory() as uow:
            session = uow.sessions.find(session_id)
            if session is None or session.device_id != device_id:
                msg = "Session inconnue sur cet appareil"
                raise Unauthenticated(msg)
            if session.revoked:
                return
            presented = self._secrets.digest(secret)
            successor = self._secrets.digest(self._secrets.successor(secret))
            legitimate = session.matches(presented) or (
                session.is_active(now)
                and session.judge_refresh(presented, successor, device_id, now)
                is RefreshVerdict.REPLAY
            )
            reason = RevocationReason.LOGOUT if legitimate else RevocationReason.REFRESH_REUSE
            session.revoke(now, reason)
            uow.sessions.update(session)
            uow.commit()
