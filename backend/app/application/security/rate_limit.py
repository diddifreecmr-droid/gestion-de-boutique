"""Limitation de débit des routes `/auth/*`, par adresse IP et par numéro (specs § 8.1).

Elle s'ajoute au blocage du compte (5 codes faux → 15 min) : celui-ci protège **un** compte,
la limitation freine celui qui essaie beaucoup de numéros depuis une même adresse, ou un
numéro depuis beaucoup d'adresses.

- `RateLimiter` est un **port** : l'adaptateur livré (`infrastructure/rate_limit.py`) compte en
  mémoire, **par processus** ; avec plusieurs instances de l'API, un stockage partagé (Redis…)
  prendra sa place sans toucher aux routes.
- `AuthThrottle` applique les règles (seuils de `Settings`, voir `.env.example`) et lève
  `RateLimited` (429 `RATE_LIMITED`, `Retry-After`). Désactivée en `ENVIRONMENT=test` par
  défaut (la composition root ne la branche pas).
- Clé d'un numéro : ses 9 derniers chiffres, quelle que soit la façon de l'écrire
  (`690 00 00 00`, `+237690000000`) ; une saisie sans chiffre est comptée sous sa forme brute.
"""

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.application.ports.clock import Clock
from app.application.security.errors import RateLimited

PHONE_KEY_DIGITS = 9


@dataclass(frozen=True, slots=True)
class RateLimitRule:
    name: str
    limit: int
    window: timedelta

    def __post_init__(self) -> None:
        if self.limit < 1 or self.window <= timedelta(0):
            msg = f"Règle {self.name} : limite ≥ 1 et fenêtre > 0 attendues"
            raise ValueError(msg)


class RateLimiter(ABC):
    @abstractmethod
    def hit(self, rule: RateLimitRule, key: str, now: datetime) -> timedelta | None:
        """Compte une demande ; `None` si elle passe, sinon l'attente avant la suivante."""


def phone_key(text: str) -> str:
    digits = "".join(char for char in text if char.isascii() and char.isdigit())
    return digits[-PHONE_KEY_DIGITS:] if digits else text.strip().casefold()[:32]


class AuthThrottle:
    def __init__(
        self,
        limiter: RateLimiter,
        clock: Clock,
        *,
        per_ip: RateLimitRule,
        per_phone: RateLimitRule,
    ) -> None:
        self._limiter = limiter
        self._clock = clock
        self.per_ip = per_ip
        self.per_phone = per_phone

    def check_ip(self, ip: str) -> None:
        self._check(self.per_ip, ip or "unknown")

    def check_phone(self, phone: str) -> None:
        self._check(self.per_phone, phone_key(phone))

    def _check(self, rule: RateLimitRule, key: str) -> None:
        wait = self._limiter.hit(rule, key, self._clock.now())
        if wait is not None:
            raise RateLimited(max(1, math.ceil(wait.total_seconds())))
