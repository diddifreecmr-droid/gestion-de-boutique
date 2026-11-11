"""Horloge contrôlable pour les tests et la démo (port `Clock`)."""

from datetime import datetime, timedelta

from app.application.ports.clock import Clock
from app.domain.shared.business_day import require_aware


class FixedClock(Clock):
    """Instant figé, déplacé explicitement ; un instant naïf est refusé (`ValueError`)."""

    def __init__(self, instant: datetime) -> None:
        self._now = require_aware(instant)

    def now(self) -> datetime:
        return self._now

    def move_to(self, instant: datetime) -> None:
        self._now = require_aware(instant)

    def advance(self, delta: timedelta) -> datetime:
        """Avance (ou recule si négatif) l'horloge et renvoie le nouvel instant."""
        if not isinstance(delta, timedelta):
            msg = f"advance attend un timedelta, reçu {type(delta).__name__}"
            raise TypeError(msg)
        self._now = self._now + delta
        return self._now
