"""Statut d'un compte (Actif, Bloqué, Désactivé — CDC § 20.1) et transitions d'administration.

Extrait de `user.py` (limite de 200 lignes) : `UserStatusMixin` porte la lecture du statut,
le blocage du **login** (`login_lockout`) et la désactivation (RG-D06). Il ne déclare aucun
champ : ceux-ci sont ceux de la dataclass `User`.
"""

from datetime import datetime
from enum import StrEnum

from app.domain.identity.events import IdentityEvents, UserDisabled, UserReactivated
from app.domain.identity.lockout import LockoutCounter
from app.domain.shared.errors import InvalidStateTransition
from app.domain.shared.ids import UserId


class UserStatus(StrEnum):
    ACTIVE = "active"
    LOCKED = "locked"
    DISABLED = "disabled"


class UserStatusMixin:
    """Comportement de statut de `User` ; attributs fournis par la dataclass."""

    id: UserId
    status: UserStatus
    login_lockout: LockoutCounter
    events: IdentityEvents

    @property
    def failed_attempts(self) -> int:
        """Codes faux consécutifs **à la connexion** (« Essais faux » du CDC)."""
        return self.login_lockout.failures

    @property
    def locked_until(self) -> datetime | None:
        """Fin du blocage du login (`USER.locked_until`, specs § 5.2)."""
        return self.login_lockout.locked_until

    def status_at(self, now: datetime) -> UserStatus:
        if self.status is UserStatus.LOCKED and self._active_lock_end(now) is None:
            return UserStatus.ACTIVE
        return self.status

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
        """Fin du blocage du login s'il court encore (statut `LOCKED` seulement)."""
        if self.status is not UserStatus.LOCKED:
            return None
        return self.login_lockout.lock_end(now)

    def _release_expired_lock(self, now: datetime) -> None:
        if self.status is UserStatus.LOCKED and self._active_lock_end(now) is None:
            self._clear_lock()

    def _clear_lock(self) -> None:
        """Remet le compteur du login à zéro ; un compte désactivé le reste."""
        if self.status is UserStatus.LOCKED:
            self.status = UserStatus.ACTIVE
        self.login_lockout = LockoutCounter()
