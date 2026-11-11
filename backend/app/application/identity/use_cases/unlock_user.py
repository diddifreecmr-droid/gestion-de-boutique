"""UC-SOC-02 cas particulier — Le propriétaire débloque un compte (recette SEC-L07).

Le blocage et le compteur d'essais sont remis à zéro ; la connexion est possible aussitôt.
Un compte qui n'est pas (ou plus) bloqué → `InvalidStateTransition` (422).
"""

from app.application.identity.uow import IdentityUnitOfWorkFactory
from app.application.identity.use_cases.member_access import MemberAccess
from app.application.ports.clock import Clock
from app.application.security.actor import Actor
from app.domain.shared.ids import UserId


class UnlockUser:
    def __init__(
        self, uow_factory: IdentityUnitOfWorkFactory, access: MemberAccess, clock: Clock
    ) -> None:
        self._uow_factory = uow_factory
        self._access = access
        self._clock = clock

    def execute(self, actor: Actor, target: UserId) -> None:
        self._access.require(actor, target)
        with self._uow_factory() as uow:
            user = uow.users.get(target)
            user.unlock(self._clock.now(), by=actor.user_id)
            uow.users.update(user)
            uow.commit()
