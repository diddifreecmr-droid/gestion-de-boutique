"""RG-D07 — Déconnecter à distance tous les appareils d'un utilisateur (recette SEC-R01, R06).

Toutes les sessions encore ouvertes de la cible sont révoquées (motif `REMOTE`, auteur
`actor.user_id`) ; le jeton d'accès en cours est refusé dès la requête suivante car la session
est relue à chaque requête (SEC-R02). La révocation n'est pas une désactivation : la cible peut
se reconnecter avec son code (SEC-R04). Renvoie le nombre de sessions révoquées.
"""

from app.application.identity.uow import IdentityUnitOfWorkFactory
from app.application.identity.use_cases.member_access import MemberAccess
from app.application.ports.clock import Clock
from app.application.security.actor import Actor
from app.domain.identity.events import RevocationReason
from app.domain.shared.ids import UserId


class RevokeUserDevices:
    def __init__(
        self, uow_factory: IdentityUnitOfWorkFactory, access: MemberAccess, clock: Clock
    ) -> None:
        self._uow_factory = uow_factory
        self._access = access
        self._clock = clock

    def execute(self, actor: Actor, target: UserId) -> int:
        self._access.require(actor, target)
        now = self._clock.now()
        with self._uow_factory() as uow:
            uow.users.get(target)
            open_sessions = [s for s in uow.sessions.for_user(target) if not s.revoked]
            for session in open_sessions:
                session.revoke(now, RevocationReason.REMOTE, by=actor.user_id)
                uow.sessions.update(session)
            uow.commit()
        return len(open_sessions)
