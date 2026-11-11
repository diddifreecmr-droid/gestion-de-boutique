"""`RateLimiter` en mémoire, **par processus** : fenêtre glissante exacte (journal des instants).

Chaque `(règle, clé)` garde les instants de ses demandes encore dans la fenêtre ; au-delà de la
limite, la demande est refusée (et **non** comptée : attendre suffit à repasser) avec le délai
jusqu'à la sortie de la plus ancienne. Mémoire bornée : les clés sans demande récente sont
purgées toutes les `SWEEP_EVERY` demandes. Plusieurs instances de l'API ont chacune leur
compteur : un adaptateur partagé (Redis…) remplacera celui-ci derrière le même port.
"""

import threading
from collections import deque
from datetime import datetime, timedelta

from app.application.security.rate_limit import RateLimiter, RateLimitRule
from app.domain.shared.business_day import require_aware

SWEEP_EVERY = 1_000


class InMemoryRateLimiter(RateLimiter):
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._hits: dict[tuple[str, str], deque[datetime]] = {}
        self._windows: dict[str, timedelta] = {}
        self._since_sweep = 0

    def hit(self, rule: RateLimitRule, key: str, now: datetime) -> timedelta | None:
        instant = require_aware(now)
        with self._lock:
            self._windows[rule.name] = rule.window
            self._sweep(instant)
            hits = self._hits.setdefault((rule.name, key), deque())
            while hits and hits[0] <= instant - rule.window:
                hits.popleft()
            if len(hits) >= rule.limit:
                return hits[0] + rule.window - instant
            hits.append(instant)
            return None

    def _sweep(self, now: datetime) -> None:
        self._since_sweep += 1
        if self._since_sweep < SWEEP_EVERY:
            return
        self._since_sweep = 0
        stale = [
            bucket
            for bucket, hits in self._hits.items()
            if not hits or hits[-1] <= now - self._windows[bucket[0]]
        ]
        for bucket in stale:
            del self._hits[bucket]
