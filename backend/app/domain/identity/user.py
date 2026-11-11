"""Agrégat `User` : compte **plateforme** (téléphone unique sur toute la plateforme, CDC § 20.1).

- `secret_hash` : empreinte Argon2id du code à 6 chiffres, ou du mot de passe pour
  l'administrateur plateforme (colonne `pin_hash` de specs § 5.2). Jamais le secret en clair.
- Statut stocké : `ACTIVE`, `LOCKED` (avec `locked_until`) ou `DISABLED`. Un blocage échu
  n'est pas réécrit en base : `status_at(now)` le lit comme `ACTIVE`, et la prochaine tentative
  repart d'un compteur à zéro.
- Blocage : `MAX_FAILED_ATTEMPTS` essais faux consécutifs → bloqué `LOCK_DURATION` (UC-SOC-02 ;
  même règle pour l'admin, § 15.1). Une connexion réussie remet le compteur à 0 (SEC-L06).
- Code provisoire (`must_change_pin`) : vrai à la création et après une remise à zéro (H14).
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum

from app.domain.identity.errors import AccountDisabled, AccountLocked, PinChangeRequired
from app.domain.identity.events import (
    IdentityEvents,
    LoginFailed,
    LoginSucceeded,
    PinChanged,
    PinReset,
    SessionId,
    UserDisabled,
    UserLocked,
    UserReactivated,
    UserUnlocked,
)
from app.domain.identity.phone import PhoneNumber
from app.domain.shared.business_day import require_aware
from app.domain.shared.errors import InvalidStateTransition, ValidationFailed
from app.domain.shared.ids import DeviceId, UserId

MAX_FAILED_ATTEMPTS = 5
LOCK_DURATION = timedelta(minutes=15)
NAME_MAX_LENGTH = 120


class UserStatus(StrEnum):
    ACTIVE = "active"
    LOCKED = "locked"
    DISABLED = "disabled"


@dataclass(eq=False)
class User:
    id: UserId
    phone: PhoneNumber
    name: str
    secret_hash: str
    is_platform_admin: bool = False
    must_change_pin: bool = True
    status: UserStatus = UserStatus.ACTIVE
    failed_attempts: int = 0
    locked_until: datetime | None = None
    last_login_at: datetime | None = None
    version: int = 0
    events: IdentityEvents = field(default_factory=IdentityEvents, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.phone, PhoneNumber):
            msg = "User.phone doit être un PhoneNumber"
            raise TypeError(msg)
        self.name = self.name.strip() if isinstance(self.name, str) else ""
        if not self.name or len(self.name) > NAME_MAX_LENGTH:
            msg = f"Nom obligatoire, {NAME_MAX_LENGTH} caractères au plus"
            raise ValidationFailed(msg, details={"field": "name"})
        if not self.secret_hash:
            msg = "Un utilisateur a toujours une empreinte de secret"
            raise ValueError(msg)

    @classmethod
    def register(
        cls,
        *,
        phone: PhoneNumber,
        name: str,
        secret_hash: str,
        is_platform_admin: bool = False,
        must_change_pin: bool = True,
    ) -> "User":
        """Nouveau compte ; le secret initial est provisoire par défaut (H14)."""
        return cls(
            UserId.new(),
            phone,
            name,
            secret_hash,
            is_platform_admin=is_platform_admin,
            must_change_pin=must_change_pin,
        )

    def status_at(self, now: datetime) -> UserStatus:
        if self.status is UserStatus.LOCKED and self._active_lock_end(now) is None:
            return UserStatus.ACTIVE
        return self.status

    def ensure_not_locked(self, now: datetime) -> None:
        """Lève `AccountLocked` (avec la fin du blocage) tant que le blocage court."""
        until = self._active_lock_end(now)
        if until is not None:
            raise AccountLocked(until)

    def ensure_active(self) -> None:
        if self.status is UserStatus.DISABLED:
            raise AccountDisabled

    def ensure_pin_changed(self) -> None:
        if self.must_change_pin:
            raise PinChangeRequired

    def record_failed_attempt(self, now: datetime, device_id: DeviceId) -> None:
        self.ensure_not_locked(now)
        self._release_expired_lock(now)
        self.failed_attempts += 1
        self.events.record(
            LoginFailed(
                user_id=self.id,
                occurred_at=now,
                device_id=device_id,
                failed_attempts=self.failed_attempts,
            )
        )
        if self.failed_attempts >= MAX_FAILED_ATTEMPTS and self.status is UserStatus.ACTIVE:
            self.status = UserStatus.LOCKED
            self.locked_until = require_aware(now) + LOCK_DURATION
            self.events.record(
                UserLocked(user_id=self.id, occurred_at=now, locked_until=self.locked_until)
            )

    def record_login(self, now: datetime, device_id: DeviceId, session_id: SessionId) -> None:
        self.ensure_not_locked(now)
        self.ensure_active()
        self._release_expired_lock(now)
        self.failed_attempts = 0
        self.last_login_at = require_aware(now)
        self.events.record(
            LoginSucceeded(
                user_id=self.id, occurred_at=now, device_id=device_id, session_id=session_id
            )
        )

    def rehash(self, secret_hash: str) -> None:
        """Remplace l'empreinte par une plus robuste (même secret) ; aucun événement."""
        if not secret_hash:
            msg = "Empreinte vide refusée"
            raise ValueError(msg)
        self.secret_hash = secret_hash

    def change_secret(self, secret_hash: str, now: datetime) -> None:
        self.rehash(secret_hash)
        self.must_change_pin = False
        self.events.record(PinChanged(user_id=self.id, occurred_at=now))

    def reset_secret(self, temporary_hash: str, now: datetime, by: UserId) -> None:
        """Code provisoire : à changer à la prochaine connexion ; lève aussi le blocage."""
        self.rehash(temporary_hash)
        self.must_change_pin = True
        self._clear_lock()
        self.events.record(PinReset(user_id=self.id, occurred_at=now, by=by))

    def unlock(self, now: datetime, by: UserId) -> None:
        if self.status_at(now) is not UserStatus.LOCKED:
            msg = "Ce compte n'est pas bloqué"
            raise InvalidStateTransition(msg, details={"status": self.status_at(now).value})
        self._clear_lock()
        self.events.record(UserUnlocked(user_id=self.id, occurred_at=now, by=by))

    def disable(self, now: datetime, by: UserId) -> None:
        if self.status is UserStatus.DISABLED:
            msg = "Ce compte est déjà désactivé"
            raise InvalidStateTransition(msg, details={"status": self.status.value})
        self.status = UserStatus.DISABLED
        self.events.record(UserDisabled(user_id=self.id, occurred_at=now, by=by))

    def reactivate(self, now: datetime, by: UserId) -> None:
        if self.status is not UserStatus.DISABLED:
            msg = "Ce compte n'est pas désactivé"
            raise InvalidStateTransition(msg, details={"status": self.status.value})
        self.status = UserStatus.ACTIVE
        self._clear_lock()
        self.events.record(UserReactivated(user_id=self.id, occurred_at=now, by=by))

    def _active_lock_end(self, now: datetime) -> datetime | None:
        """Fin du blocage s'il court encore à `now`, sinon `None`."""
        if self.status is not UserStatus.LOCKED or self.locked_until is None:
            return None
        return self.locked_until if require_aware(now) < self.locked_until else None

    def _release_expired_lock(self, now: datetime) -> None:
        if self.status is UserStatus.LOCKED and self._active_lock_end(now) is None:
            self._clear_lock()

    def _clear_lock(self) -> None:
        """Remet le compteur à zéro ; un compte désactivé le reste."""
        if self.status is UserStatus.LOCKED:
            self.status = UserStatus.ACTIVE
        self.failed_attempts = 0
        self.locked_until = None
