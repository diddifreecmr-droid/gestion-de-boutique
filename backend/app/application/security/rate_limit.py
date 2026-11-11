"""Limitation de débit des routes `/auth/*`, par adresse IP et par numéro (specs § 8.1, SEC-L09).

Elle s'ajoute au blocage du compte (5 codes faux → 15 min) : celui-ci protège **un** compte,
la limitation freine celui qui essaie beaucoup de numéros depuis une même adresse, ou un
numéro depuis beaucoup d'adresses.

- `RateLimiter` est un **port** : l'adaptateur livré (`infrastructure/rate_limit.py`) compte en
  mémoire, **par processus** ; avec plusieurs instances de l'API, un stockage partagé (Redis…)
  prendra sa place sans toucher aux routes. L'heure est fournie par l'appelant (port `Clock`).
- `AuthThrottle` applique une règle **par route** (`AuthRateRules`, seuils de `Settings`, voir
  `.env.example`) et lève `RateLimited` (429 `RATE_LIMITED`, `Retry-After`). `/auth/logout`
  n'est pas limité (il ne révèle rien et ne fait que fermer une session). Désactivée en
  `ENVIRONMENT=test` par défaut (la composition root ne la branche pas).
- Clé d'un numéro : sa forme **E.164** (`PhoneNumber.parse`), donc `690 00 00 00`,
  `+237690000000` et `00237690000000` partagent un compteur. Saisie invalide : clé fixe
  `invalid@<ip>` (voir `phone_key`).
"""

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.application.ports.clock import Clock
from app.application.security.errors import RateLimited
from app.domain.identity.phone import PhoneNumber
from app.domain.shared.errors import ValidationFailed

UNKNOWN_IP = "unknown"


@dataclass(frozen=True, slots=True)
class RateLimitRule:
    name: str
    limit: int
    window: timedelta

    def __post_init__(self) -> None:
        if self.limit < 1 or self.window <= timedelta(0):
            msg = f"Règle {self.name} : limite ≥ 1 et fenêtre > 0 attendues"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthRateRules:
    """Une règle par route limitée ; les noms doivent être distincts (compteurs séparés)."""

    login_ip: RateLimitRule
    login_phone: RateLimitRule
    refresh_ip: RateLimitRule
    change_pin_ip: RateLimitRule

    def __post_init__(self) -> None:
        names = [r.name for r in (self.login_ip, self.login_phone, self.refresh_ip,
                                  self.change_pin_ip)]  # fmt: skip
        if len(set(names)) != len(names):
            msg = f"Noms de règles de débit en double : {names}"
            raise ValueError(msg)


class RateLimiter(ABC):
    @abstractmethod
    def hit(self, rule: RateLimitRule, key: str, now: datetime) -> timedelta | None:
        """Compte une demande ; `None` si elle passe, sinon l'attente avant la suivante.

        Une demande refusée n'est **pas** comptée : attendre `retry_after` suffit à repasser.
        """


def phone_key(text: str, ip: str) -> str:
    """Clé « numéro » : E.164 si la saisie est un numéro valide, sinon `invalid@<ip>`.

    Une saisie invalide ne désigne aucun compte (la connexion la refuse en 401) : la compter
    sous sa forme brute laisserait un attaquant créer une clé neuve par requête (contournement
    de la règle et mémoire non bornée). Toutes les saisies invalides d'une même adresse
    partagent donc **un** compteur ; les numéros valides des autres utilisateurs de cette
    adresse (NAT, cybercafé) gardent le leur.
    """
    try:
        return PhoneNumber.parse(text).e164
    except ValidationFailed:
        return f"invalid@{ip or UNKNOWN_IP}"


class AuthThrottle:
    def __init__(self, limiter: RateLimiter, clock: Clock, rules: AuthRateRules) -> None:
        self._limiter = limiter
        self._clock = clock
        self.rules = rules

    def check_login_ip(self, ip: str) -> None:
        self._check(self.rules.login_ip, ip or UNKNOWN_IP)

    def check_login_phone(self, phone: str, ip: str) -> None:
        self._check(self.rules.login_phone, phone_key(phone, ip))

    def check_refresh(self, ip: str) -> None:
        self._check(self.rules.refresh_ip, ip or UNKNOWN_IP)

    def check_change_pin(self, ip: str) -> None:
        self._check(self.rules.change_pin_ip, ip or UNKNOWN_IP)

    def _check(self, rule: RateLimitRule, key: str) -> None:
        wait = self._limiter.hit(rule, key, self._clock.now())
        if wait is not None:
            raise RateLimited(max(1, math.ceil(wait.total_seconds())))
