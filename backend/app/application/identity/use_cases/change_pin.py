"""UC-SOC-07 — Changer son code secret (recette PIN-01, PIN-02).

Contrôles, dans cet ordre :

1. nouvelle saisie ≠ confirmation → `ValidationFailed` (`new_pin_confirmation`) ;
2. politique : code à 6 chiffres non simple (`PinTooSimple`), ou, pour l'administrateur
   plateforme, mot de passe fort (`PasswordTooWeak`) — voir `domain/identity/credentials.py` ;
3. changement de code bloqué → `PinChangeLocked` (423, `details.until`), sans vérifier le
   code actuel ;
4. code actuel faux → compté dans le compteur **propre au changement de code** (décision
   client du 11/11/2026), validé en base, puis `CurrentPinInvalid` (422, jamais 401 : le
   client y verrait une session expirée) avec `remaining_attempts`. Le 5ᵉ échec renvoie
   encore 422 avec `remaining_attempts = 0` et pose le blocage : l'appel **suivant** reçoit
   `PinChangeLocked` (423) ;
5. nouveau = actuel → `ValidationFailed` (`new_pin`).

Ce blocage ne touche que cette route : la session, le login et les autres routes continuent.
Inversement, un blocage du login n'empêche pas de changer son code depuis une session ouverte,
et le login ne remet pas ce compteur à zéro (ni l'inverse). Succès : nouvelle empreinte,
`must_change_pin` effacé, compteur du changement de code à 0. Les sessions restent ouvertes.
"""

from dataclasses import dataclass

from app.application.identity.ports import PasswordHasher
from app.application.identity.uow import IdentityUnitOfWorkFactory
from app.application.identity.use_cases.authenticate import AuthenticatedUser
from app.application.ports.clock import Clock
from app.domain.identity.credentials import validate_new_password, validate_new_pin
from app.domain.identity.errors import CurrentPinInvalid
from app.domain.identity.lockout import MAX_FAILED_ATTEMPTS
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
            user.ensure_pin_change_allowed(now)
            if not self._hasher.verify(user.secret_hash, command.current):
                user.record_failed_pin_change(now, identity.device_id)
                uow.users.update(user)
                uow.commit()
                remaining = max(MAX_FAILED_ATTEMPTS - user.pin_change_lockout.failures, 0)
                raise CurrentPinInvalid(remaining)
            if command.new == command.current:
                msg = "Le nouveau code doit être différent de l'actuel"
                raise ValidationFailed(msg, details={"field": "new_pin"})
            user.change_secret(self._hasher.hash(command.new), now)
            uow.users.update(user)
            uow.commit()
