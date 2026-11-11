"""`RateLimiter` en mémoire, **par processus** : fenêtre glissante exacte (journal des instants).

Chaque `(règle, clé)` garde les instants de ses demandes encore dans la fenêtre ; au-delà de la
limite, la demande est refusée (et **non** comptée : attendre suffit à repasser) avec le délai
jusqu'à la sortie de la plus ancienne. Mémoire bornée : les clés sans demande récente sont
purgées toutes les `sweep_every` demandes (défaut `SWEEP_EVERY`). Thread-safe : un verrou
unique protège les compteurs (FastAPI exécute les routes synchrones dans un pool de threads).
Plusieurs instances de l'API ont chacune leur compteur : un adaptateur partagé (Redis…)
remplacera celui-ci derrière le même port.
"""

import threading
from collections import deque
from datetime import datetime, timedelta

from app.application.security.rate_limit import RateLimiter, RateLimitRule
from app.domain.shared.business_day import require_aware

SWEEP_EVERY = 1_000


class InMemoryRateLimiter(RateLimiter):
    def __init__(self, *, sweep_every: int = SWEEP_EVERY) -> None:
        if sweep_every < 1:
            msg = "sweep_every doit valoir au moins 1"
            raise ValueError(msg)
        self._sweep_every = sweep_every
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

    @property
    def tracked_keys(self) -> int:
        """Nombre de couples `(règle, clé)` en mémoire (surveillance, tests de purge)."""
        with self._lock:
            return len(self._hits)

    def _sweep(self, now: datetime) -> None:
        self._since_sweep += 1
        if self._since_sweep < self._sweep_every:
            return
        self._since_sweep = 0
        stale = [
            bucket
            for bucket, hits in self._hits.items()
            if not hits or hits[-1] <= now - self._windows[bucket[0]]
        ]
        for bucket in stale:
            del self._hits[bucket]
