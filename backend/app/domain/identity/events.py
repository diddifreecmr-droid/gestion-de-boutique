"""Événements de l'identité, destinés au futur journal d'actions (T09).

Ils ne dérivent **pas** de `DomainEvent` : celui-ci exige un `shop_id`, alors qu'un utilisateur
et ses sessions sont **plateforme** (un même compte peut appartenir à plusieurs boutiques). Le
handler du journal (T09) décidera dans quelles boutiques inscrire chaque événement (celles où
l'utilisateur est rattaché, ou celle de l'acteur `by`).
"""

from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from app.domain.shared.business_day import require_aware
from app.domain.shared.ids import DeviceId, EntityId, EventId, UserId


class SessionId(EntityId):
    """Session d'un appareil (`DEVICE_SESSION`, claim `sid` du jeton d'accès)."""

    __slots__ = ()


class RevocationReason(StrEnum):
    LOGOUT = "logout"
    """Déconnexion volontaire depuis l'appareil."""
    REMOTE = "remote"
    """Déconnexion à distance par le propriétaire (RG-D07)."""
    REFRESH_REUSE = "refresh_reuse"
    """Jeton de rafraîchissement déjà tourné présenté à nouveau (vol présumé)."""


@dataclass(frozen=True, kw_only=True)
class IdentityEvent:
    """Base abstraite : `user_id` concerné, `occurred_at` (ramené en UTC), `event_id`."""

    user_id: UserId
    occurred_at: datetime
    event_id: EventId = field(default_factory=EventId.new)

    def __post_init__(self) -> None:
        if type(self) is IdentityEvent:
            msg = "IdentityEvent est abstraite : déclarer un événement typé"
            raise TypeError(msg)
        if not isinstance(self.user_id, UserId):
            msg = f"user_id doit être un UserId, reçu {type(self.user_id).__name__}"
            raise TypeError(msg)
        object.__setattr__(self, "occurred_at", require_aware(self.occurred_at))


class IdentityEvents:
    """File ordonnée des événements en attente d'un agrégat de l'identité."""

    __slots__ = ("_pending",)

    def __init__(self) -> None:
        self._pending: list[IdentityEvent] = []

    def record(self, event: IdentityEvent) -> None:
        if not isinstance(event, IdentityEvent):
            msg = f"Seul un IdentityEvent peut être enregistré, reçu {type(event).__name__}"
            raise TypeError(msg)
        self._pending.append(event)

    def pull(self) -> tuple[IdentityEvent, ...]:
        events = tuple(self._pending)
        self._pending.clear()
        return events

    def __len__(self) -> int:
        return len(self._pending)

    def __iter__(self) -> Iterator[IdentityEvent]:
        return iter(tuple(self._pending))


@dataclass(frozen=True, kw_only=True)
class LoginSucceeded(IdentityEvent):
    device_id: DeviceId
    session_id: SessionId


@dataclass(frozen=True, kw_only=True)
class LoginFailed(IdentityEvent):
    device_id: DeviceId
    failed_attempts: int


@dataclass(frozen=True, kw_only=True)
class UserLocked(IdentityEvent):
    locked_until: datetime


@dataclass(frozen=True, kw_only=True)
class UserUnlocked(IdentityEvent):
    by: UserId


@dataclass(frozen=True, kw_only=True)
class PinChanged(IdentityEvent):
    """Code (ou mot de passe admin) changé par l'utilisateur lui-même."""


@dataclass(frozen=True, kw_only=True)
class PinReset(IdentityEvent):
    """Code provisoire attribué par le propriétaire `by`."""

    by: UserId


@dataclass(frozen=True, kw_only=True)
class UserDisabled(IdentityEvent):
    by: UserId


@dataclass(frozen=True, kw_only=True)
class UserReactivated(IdentityEvent):
    by: UserId


@dataclass(frozen=True, kw_only=True)
class SessionRevokedEvent(IdentityEvent):
    session_id: SessionId
    device_id: DeviceId
    reason: RevocationReason
    by: UserId | None = None
