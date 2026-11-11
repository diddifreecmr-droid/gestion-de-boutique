"""UC-SOC-02 — Se connecter (specs § 8.1, recette SEC-L01 à SEC-L08, SEC-X01).

Ordre des contrôles, choisi pour ne rien révéler qui ne soit exigé :

1. numéro illisible ou inconnu → `InvalidCredentials` (401, message générique), après un
   hachage factice pour que la durée de réponse ne trahisse pas l'existence du compte ;
2. compte bloqué → `AccountLocked` (423, `details.until`) **sans** vérifier le secret : un
   code juste ne doit pas pouvoir être distingué d'un faux pendant le blocage ;
3. secret faux (ou d'un mauvais type : code pour l'admin, mot de passe pour un membre) →
   essai compté et **validé en base**, puis `InvalidCredentials` ; au 5ᵉ, blocage 15 min ;
4. compte désactivé (RG-D06) → `AccountDisabled`, seulement après un secret juste : statut
   du compte **ou** aucun rattachement utilisable (désactivation par boutique, T10) ;
5. succès → compteur à 0, session de l'appareil créée ou réutilisée, jetons émis.
"""

from dataclasses import dataclass
from enum import StrEnum
from functools import cached_property

from app.application.identity.ports import MembershipDirectory, PasswordHasher
from app.application.identity.reachability import require_reachable
from app.application.identity.sessions import IssuedSession, SessionIssuer
from app.application.identity.uow import IdentityUnitOfWorkFactory
from app.application.ports.clock import Clock
from app.domain.identity.errors import InvalidCredentials
from app.domain.identity.phone import PhoneNumber
from app.domain.identity.user import User
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.ids import DeviceId

_TIMING_EQUALIZER = "egalisation-du-temps-de-reponse"


class CredentialKind(StrEnum):
    PIN = "pin"
    """Code à 6 chiffres : utilisateurs de boutique."""
    PASSWORD = "password"
    """Mot de passe : administrateur plateforme (§ 15.1)."""


def expected_kind(user: User) -> CredentialKind:
    return CredentialKind.PASSWORD if user.is_platform_admin else CredentialKind.PIN


@dataclass(frozen=True, slots=True, kw_only=True)
class LoginCommand:
    phone: str
    secret: str
    kind: CredentialKind
    device_id: DeviceId
    device_label: str


class Login:
    def __init__(
        self,
        uow_factory: IdentityUnitOfWorkFactory,
        hasher: PasswordHasher,
        issuer: SessionIssuer,
        clock: Clock,
        memberships: MembershipDirectory,
    ) -> None:
        self._uow_factory = uow_factory
        self._hasher = hasher
        self._issuer = issuer
        self._clock = clock
        self._memberships = memberships

    @cached_property
    def _dummy_hash(self) -> str:
        """Empreinte factice, calculée au premier numéro inconnu (pas au démarrage)."""
        return self._hasher.hash(_TIMING_EQUALIZER)

    def execute(self, command: LoginCommand) -> IssuedSession:
        now = self._clock.now()
        try:
            phone = PhoneNumber.parse(command.phone)
        except ValidationFailed as exc:
            self._hasher.verify(self._dummy_hash, command.secret)
            raise InvalidCredentials from exc
        with self._uow_factory() as uow:
            user = uow.users.find_by_phone(phone)
            if user is None:
                self._hasher.verify(self._dummy_hash, command.secret)
                raise InvalidCredentials
            user.ensure_not_locked(now)
            secret_ok = self._hasher.verify(user.secret_hash, command.secret)
            if not secret_ok or command.kind is not expected_kind(user):
                user.record_failed_attempt(now, command.device_id)
                uow.users.update(user)
                uow.commit()
                raise InvalidCredentials
            user.ensure_active()
            require_reachable(self._memberships, user)
            if self._hasher.needs_rehash(user.secret_hash):
                user.rehash(self._hasher.hash(command.secret))
            issued = self._issuer.open(uow, user, command.device_id, command.device_label, now)
            user.record_login(now, command.device_id, issued.session_id)
            uow.users.update(user)
            uow.commit()
        return issued
