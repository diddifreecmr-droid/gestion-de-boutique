"""Agrégat `DeviceSession` : une session ouverte sur un appareil (CDC § 20.1, specs § 5.2).

- `refresh_hash` : empreinte du **seul** jeton de rafraîchissement valide ; le jeton en clair
  n'est jamais stocké. Chaque rafraîchissement le remplace (rotation, specs § 8.1).
- `expires_at` : fin de validité. Glissante (`sliding=True`, utilisateurs de boutique : chaque
  rotation la repousse de la durée de vie) ou absolue (`sliding=False`, admin plateforme : 8 h
  depuis la connexion, § 15.1).
- `last_seen` : dernière activité, mise à jour à la connexion et à chaque rafraîchissement
  (granularité : la durée du jeton d'accès, pour ne pas écrire à chaque requête).
- Une session révoquée ne revit jamais : une nouvelle connexion en ouvre une autre.
"""

import hmac
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.domain.identity.events import (
    IdentityEvents,
    RevocationReason,
    SessionId,
    SessionRevokedEvent,
)
from app.domain.shared.business_day import require_aware
from app.domain.shared.errors import InvalidStateTransition, ValidationFailed
from app.domain.shared.ids import DeviceId, UserId

DEVICE_LABEL_MAX_LENGTH = 100


def _clean_label(label: str) -> str:
    cleaned = " ".join(label.split()) if isinstance(label, str) else ""
    if not cleaned or len(cleaned) > DEVICE_LABEL_MAX_LENGTH:
        msg = f"Description d'appareil obligatoire, {DEVICE_LABEL_MAX_LENGTH} caractères au plus"
        raise ValidationFailed(msg, details={"field": "device_label"})
    return cleaned


def _require_lifetime(lifetime: timedelta) -> timedelta:
    if lifetime <= timedelta(0):
        msg = f"Durée de session strictement positive attendue, reçu {lifetime}"
        raise ValueError(msg)
    return lifetime


@dataclass(eq=False)
class DeviceSession:
    id: SessionId
    user_id: UserId
    device_id: DeviceId
    device_label: str
    refresh_hash: str
    created_at: datetime
    last_seen: datetime
    expires_at: datetime
    sliding: bool
    revoked: bool = False
    revoked_at: datetime | None = None
    version: int = 0
    events: IdentityEvents = field(default_factory=IdentityEvents, repr=False)

    @classmethod
    def open(
        cls,
        *,
        user_id: UserId,
        device_id: DeviceId,
        device_label: str,
        refresh_hash: str,
        now: datetime,
        lifetime: timedelta,
        sliding: bool,
    ) -> "DeviceSession":
        instant = require_aware(now)
        return cls(
            id=SessionId.new(),
            user_id=user_id,
            device_id=device_id,
            device_label=_clean_label(device_label),
            refresh_hash=refresh_hash,
            created_at=instant,
            last_seen=instant,
            expires_at=instant + _require_lifetime(lifetime),
            sliding=sliding,
        )

    def is_active(self, now: datetime) -> bool:
        return not self.revoked and require_aware(now) < self.expires_at

    def matches(self, refresh_hash: str) -> bool:
        """Comparaison à temps constant de l'empreinte présentée."""
        return hmac.compare_digest(self.refresh_hash, refresh_hash)

    def rotate(self, refresh_hash: str, now: datetime, lifetime: timedelta) -> None:
        """Nouveau jeton de rafraîchissement ; l'ancien devient une réutilisation."""
        self._require_active(now)
        instant = require_aware(now)
        self.refresh_hash = refresh_hash
        self.last_seen = instant
        if self.sliding:
            self.expires_at = instant + _require_lifetime(lifetime)

    def reopen(
        self, refresh_hash: str, device_label: str, now: datetime, lifetime: timedelta
    ) -> None:
        """Nouvelle connexion sur le même appareil : session réutilisée, validité repartie."""
        self._require_active(now)
        instant = require_aware(now)
        self.device_label = _clean_label(device_label)
        self.refresh_hash = refresh_hash
        self.last_seen = instant
        self.expires_at = instant + _require_lifetime(lifetime)

    def revoke(self, now: datetime, reason: RevocationReason, by: UserId | None = None) -> None:
        if self.revoked:
            msg = "Session déjà révoquée"
            raise InvalidStateTransition(msg, details={"session_id": str(self.id)})
        self.revoked = True
        self.revoked_at = require_aware(now)
        self.events.record(
            SessionRevokedEvent(
                user_id=self.user_id,
                occurred_at=now,
                session_id=self.id,
                device_id=self.device_id,
                reason=reason,
                by=by,
            )
        )

    def _require_active(self, now: datetime) -> None:
        if not self.is_active(now):
            msg = "Session révoquée ou expirée"
            raise InvalidStateTransition(msg, details={"session_id": str(self.id)})
