"""Rafraîchir la session d'un appareil par rotation (specs § 7.2, § 8.1, recette SEC-R03/R05).

- jeton illisible, session inconnue, d'un autre appareil sans preuve, ou expirée →
  `Unauthenticated` ;
- session révoquée → `SessionRevoked` ;
- jeton **tout juste remplacé**, même appareil, dans `REFRESH_REPLAY_GRACE` (réponse perdue,
  rechargements rapides) → le successeur actuel est renvoyé, **rien n'est écrit ni journalisé
  comme alerte** (simple trace `INFO`) ;
- jeton périmé hors de ces conditions (hors fenêtre, ou présenté par un autre appareil) →
  la session est **révoquée et la révocation validée** (journal sensible), puis
  `SessionRevoked` : le voleur comme la victime doivent se reconnecter ; les autres appareils
  ne sont pas touchés ;
- compte désactivé (RG-D06) ou sans rattachement utilisable (T10) → `AccountDisabled` ;
- sinon : rotation vers le successeur déduit du jeton, nouveau jeton d'accès. Un compte bloqué
  garde ses sessions ouvertes (le blocage vise la devinette du code, pas l'appareil connecté).

Concurrence : deux rafraîchissements simultanés du même jeton calculent le **même** successeur ;
le second se heurte au verrou optimiste (`VersionConflict`) et est rejoué sur l'état validé, où
il devient un rejeu toléré. Au-delà de `MAX_ATTEMPTS`, le conflit remonte (fail-fast).
"""

import logging

from app.application.identity.ports import MembershipDirectory, RefreshSecrets
from app.application.identity.reachability import require_reachable
from app.application.identity.sessions import IssuedSession, SessionIssuer, parse_refresh_token
from app.application.identity.uow import IdentityUnitOfWorkFactory
from app.application.ports.clock import Clock
from app.domain.identity.errors import SessionRevoked, Unauthenticated
from app.domain.identity.events import RevocationReason, SessionId
from app.domain.identity.refresh_rotation import RefreshVerdict
from app.domain.shared.errors import VersionConflict
from app.domain.shared.ids import DeviceId

MAX_ATTEMPTS = 3
_UNKNOWN = "Session inconnue sur cet appareil"
_log = logging.getLogger(__name__)


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
        session_id, secret = parse_refresh_token(refresh_token)
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                return self._attempt(session_id, secret, device_id)
            except VersionConflict:
                if attempt == MAX_ATTEMPTS:
                    raise
        msg = "MAX_ATTEMPTS doit être strictement positif"  # inatteignable : boucle non vide
        raise AssertionError(msg)

    def _attempt(self, session_id: SessionId, secret: str, device_id: DeviceId) -> IssuedSession:
        now = self._clock.now()
        presented = self._secrets.digest(secret)
        successor = self._secrets.digest(self._secrets.successor(secret))
        with self._uow_factory() as uow:
            session = uow.sessions.find(session_id)
            if session is None:
                raise Unauthenticated(_UNKNOWN)
            same_device = session.device_id == device_id
            if session.revoked and same_device:
                raise SessionRevoked
            if not session.is_active(now):
                msg = "Session expirée : reconnectez-vous" if same_device else _UNKNOWN
                raise Unauthenticated(msg)
            verdict = session.judge_refresh(presented, successor, device_id, now)
            if verdict is RefreshVerdict.FOREIGN:
                raise Unauthenticated(_UNKNOWN)
            if verdict is RefreshVerdict.REUSE:
                session.revoke(now, RevocationReason.REFRESH_REUSE)
                uow.sessions.update(session)
                uow.commit()
                raise SessionRevoked
            user = uow.users.get(session.user_id)
            user.ensure_active()
            require_reachable(self._memberships, user)
            if verdict is RefreshVerdict.REPLAY:
                _log.info("Rejeu toléré du jeton de rafraîchissement (session %s)", session.id)
                return self._issuer.replay(session, user, secret, now)
            issued = self._issuer.rotate(uow, session, user, secret, now)
            uow.commit()
        return issued
