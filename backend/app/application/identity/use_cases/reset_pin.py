"""UC-SOC-04 — Redonner un code provisoire à un membre (H14).

Le code est tiré au hasard puis vérifié contre la politique (jamais un code simple) ; il est
renvoyé **une seule fois** au propriétaire, qui le transmet ; seule son empreinte est stockée.
Le compte passe en `must_change_pin` (toute route métier → `PIN_CHANGE_REQUIRED`, y compris
pour les sessions déjà ouvertes) et son blocage éventuel est levé.
"""

from app.application.identity.ports import PasswordHasher, TemporaryPinGenerator
from app.application.identity.temporary_pins import MAX_DRAWS, draw_temporary_pin
from app.application.identity.uow import IdentityUnitOfWorkFactory
from app.application.identity.use_cases.member_access import MemberAccess
from app.application.ports.clock import Clock
from app.application.security.actor import Actor
from app.domain.shared.ids import UserId

__all__ = ["MAX_DRAWS", "ResetPin"]


class ResetPin:
    def __init__(
        self,
        uow_factory: IdentityUnitOfWorkFactory,
        access: MemberAccess,
        hasher: PasswordHasher,
        pins: TemporaryPinGenerator,
        clock: Clock,
    ) -> None:
        self._uow_factory = uow_factory
        self._access = access
        self._hasher = hasher
        self._pins = pins
        self._clock = clock

    def execute(self, actor: Actor, target: UserId) -> str:
        """Renvoie le code provisoire en clair (à afficher une fois au propriétaire)."""
        self._access.require(actor, target)
        with self._uow_factory() as uow:
            user = uow.users.get(target)
            temporary = draw_temporary_pin(self._pins, user.phone)
            user.reset_secret(self._hasher.hash(temporary), self._clock.now(), by=actor.user_id)
            uow.users.update(user)
            uow.commit()
        return temporary
