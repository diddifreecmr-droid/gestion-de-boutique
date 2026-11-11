"""UC-SOC-07 — Changer son code secret (recette PIN-01, PIN-02).

Contrôles, dans cet ordre :

1. nouvelle saisie ≠ confirmation → `ValidationFailed` (`new_pin_confirmation`) ;
2. politique : code à 6 chiffres non simple (`PinTooSimple`), ou, pour l'administrateur
   plateforme, mot de passe fort (`PasswordTooWeak`) — voir `domain/identity/credentials.py` ;
3. compte bloqué → `AccountLocked` ;
4. secret actuel faux → essai compté et validé (comme au login, PIN-02 / Q-28), puis
   `InvalidCredentials` (401) ; au 5ᵉ, blocage ;
5. nouveau = actuel → `ValidationFailed` (`new_pin`).

Succès : nouvelle empreinte, `must_change_pin` effacé. Les autres sessions restent ouvertes.
"""

from dataclasses import dataclass

from app.application.identity.ports import PasswordHasher
from app.application.identity.uow import IdentityUnitOfWorkFactory
from app.application.identity.use_cases.authenticate import AuthenticatedUser
from app.application.ports.clock import Clock
from app.domain.identity.credentials import validate_new_password, validate_new_pin
from app.domain.identity.errors import InvalidCredentials
from app.domain.identity.user import User
from app.domain.shared.errors import ValidationFailed


@dataclass(frozen=True, slots=True, kw_only=True)
class ChangePinCommand:
    current: str
    new: str
    confirmation: str


def check_new_secret(user: User, new: str) -> None:
    """Politique applicable au compte : mot de passe (admin) ou code à 6 chiffres."""
    if user.is_platform_admin:
        validate_new_password(new, user.phone, field="new_pin")
    else:
        validate_new_pin(new, user.phone, field="new_pin")


class ChangePin:
    def __init__(
        self, uow_factory: IdentityUnitOfWorkFactory, hasher: PasswordHasher, clock: Clock
    ) -> None:
        self._uow_factory = uow_factory
        self._hasher = hasher
        self._clock = clock

    def execute(self, identity: AuthenticatedUser, command: ChangePinCommand) -> None:
        now = self._clock.now()
        if command.new != command.confirmation:
            msg = "Les deux saisies du nouveau code diffèrent"
            raise ValidationFailed(msg, details={"field": "new_pin_confirmation"})
        with self._uow_factory() as uow:
            user = uow.users.get(identity.user_id)
            check_new_secret(user, command.new)
            user.ensure_not_locked(now)
            if not self._hasher.verify(user.secret_hash, command.current):
                user.record_failed_attempt(now, identity.device_id)
                uow.users.update(user)
                uow.commit()
                raise InvalidCredentials
            if command.new == command.current:
                msg = "Le nouveau code doit être différent de l'actuel"
                raise ValidationFailed(msg, details={"field": "new_pin"})
            user.change_secret(self._hasher.hash(command.new), now)
            uow.users.update(user)
            uow.commit()
