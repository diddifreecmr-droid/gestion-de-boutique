"""Agrégat `User` : compte **plateforme** (téléphone unique sur toute la plateforme, CDC § 20.1).

- `secret_hash` : empreinte Argon2id du code à 6 chiffres, ou du mot de passe pour
  l'administrateur plateforme (colonne `pin_hash` de specs § 5.2). Jamais le secret en clair.
- Statut stocké : `ACTIVE`, `LOCKED` (blocage du **login**) ou `DISABLED`. Un blocage échu
  n'est pas réécrit en base : `status_at(now)` le lit comme `ACTIVE`.
- Deux compteurs **indépendants** (`LockoutCounter`, voir `lockout.py`) :
  `login_lockout` (UC-SOC-02 ; même règle pour l'admin, § 15.1) et `pin_change_lockout`
  (codes actuels faux dans « Changer mon code », décision du 11/11/2026). Une connexion réussie
  ne remet **pas** à zéro le compteur du changement de code, et inversement ; le code provisoire
  du propriétaire (`reset_secret`) remet les deux à zéro.
- Code provisoire (`must_change_pin`) : vrai à la création et après une remise à zéro (H14).
"""

from dataclasses import dataclass, field
from datetime import datetime

from app.domain.identity.errors import (
    AccountDisabled,
    AccountLocked,
    PinChangeLocked,
    PinChangeRequired,
)
from app.domain.identity.events import (
    IdentityEvents,
    LoginFailed,
    LoginSucceeded,
    PinChanged,
    PinChangeFailed,
    PinChangeLockedEvent,
    PinReset,
    SessionId,
    UserLocked,
    UserUnlocked,
)
from app.domain.identity.lockout import LOCK_DURATION, MAX_FAILED_ATTEMPTS, LockoutCounter
from app.domain.identity.phone import PhoneNumber
from app.domain.identity.status import UserStatus, UserStatusMixin
from app.domain.shared.business_day import require_aware
from app.domain.shared.errors import InvalidStateTransition, ValidationFailed
from app.domain.shared.ids import DeviceId, UserId

__all__ = ["LOCK_DURATION", "MAX_FAILED_ATTEMPTS", "User", "UserStatus"]

NAME_MAX_LENGTH = 120


@dataclass(eq=False)
class User(UserStatusMixin):
    id: UserId
    phone: PhoneNumber
    name: str
    secret_hash: str
    is_platform_admin: bool = False
    must_change_pin: bool = True
    status: UserStatus = UserStatus.ACTIVE
    login_lockout: LockoutCounter = field(default_factory=LockoutCounter)
    pin_change_lockout: LockoutCounter = field(default_factory=LockoutCounter)
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

    def ensure_not_locked(self, now: datetime) -> None:
        """Lève `AccountLocked` (avec la fin du blocage) tant que le blocage du login court."""
        until = self._active_lock_end(now)
        if until is not None:
            raise AccountLocked(until)

    def ensure_pin_change_allowed(self, now: datetime) -> None:
        """Lève `PinChangeLocked` tant que le blocage du changement de code court."""
        until = self.pin_change_lockout.lock_end(now)
        if until is not None:
            raise PinChangeLocked(until)

    def ensure_active(self) -> None:
        if self.status is UserStatus.DISABLED:
            raise AccountDisabled

    def ensure_pin_changed(self) -> None:
        if self.must_change_pin:
            raise PinChangeRequired

    def record_failed_attempt(self, now: datetime, device_id: DeviceId) -> None:
        """Code faux à la **connexion** ; au 5ᵉ, le compte est bloqué 15 min."""
        self.ensure_not_locked(now)
        self._release_expired_lock(now)
        # Ici le statut n'est jamais LOCKED (blocage en cours refusé, échu levé) ; un blocage
        # resté sur un compte désactivé depuis est ignoré, comme avant le découpage.
        counter = LockoutCounter(self.login_lockout.failures)
        self.login_lockout = counter.after_failure(now, can_lock=self.status is UserStatus.ACTIVE)
        self.events.record(
            LoginFailed(
                user_id=self.id,
                occurred_at=now,
                device_id=device_id,
                failed_attempts=self.failed_attempts,
            )
        )
        until = self.login_lockout.locked_until
        if until is not None:
            self.status = UserStatus.LOCKED
            self.events.record(UserLocked(user_id=self.id, occurred_at=now, locked_until=until))

    def record_login(self, now: datetime, device_id: DeviceId, session_id: SessionId) -> None:
        self.ensure_not_locked(now)
        self.ensure_active()
        self._clear_lock()
        self.last_login_at = require_aware(now)
        self.events.record(
            LoginSucceeded(
                user_id=self.id, occurred_at=now, device_id=device_id, session_id=session_id
            )
        )

    def record_failed_pin_change(self, now: datetime, device_id: DeviceId) -> None:
        """Code **actuel** faux dans « Changer mon code » ; n'affecte pas le login."""
        self.ensure_pin_change_allowed(now)
        self.pin_change_lockout = self.pin_change_lockout.after_failure(now)
        counter = self.pin_change_lockout
        self.events.record(
            PinChangeFailed(
                user_id=self.id,
                occurred_at=now,
                device_id=device_id,
                failed_attempts=counter.failures,
            )
        )
        if counter.locked_until is not None:
            self.events.record(
                PinChangeLockedEvent(
                    user_id=self.id, occurred_at=now, locked_until=counter.locked_until
                )
            )

    def rehash(self, secret_hash: str) -> None:
        """Remplace l'empreinte par une plus robuste (même secret) ; aucun événement."""
        if not secret_hash:
            msg = "Empreinte vide refusée"
            raise ValueError(msg)
        self.secret_hash = secret_hash

    def change_secret(self, secret_hash: str, now: datetime) -> None:
        """Changement réussi : le compteur du changement de code repart de zéro."""
        self.rehash(secret_hash)
        self.must_change_pin = False
        self.pin_change_lockout = LockoutCounter()
        self.events.record(PinChanged(user_id=self.id, occurred_at=now))

    def reset_secret(self, temporary_hash: str, now: datetime, by: UserId) -> None:
        """Code provisoire : à changer à la prochaine connexion ; lève les **deux** blocages."""
        self.rehash(temporary_hash)
        self.must_change_pin = True
        self._clear_lock()
        self.pin_change_lockout = LockoutCounter()
        self.events.record(PinReset(user_id=self.id, occurred_at=now, by=by))

    def unlock(self, now: datetime, by: UserId) -> None:
        """Déblocage du **login** par le propriétaire (SEC-L07)."""
        if self.status_at(now) is not UserStatus.LOCKED:
            msg = "Ce compte n'est pas bloqué"
            raise InvalidStateTransition(msg, details={"status": self.status_at(now).value})
        self._clear_lock()
        self.events.record(UserUnlocked(user_id=self.id, occurred_at=now, by=by))
