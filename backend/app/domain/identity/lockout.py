"""Compteur d'essais faux et blocage temporaire, objet-valeur immuable (UC-SOC-02, UC-SOC-07).

Un même `User` en porte **deux, indépendants** (décision client du 11/11/2026) :

- `login_lockout` : codes faux à la connexion ;
- `pin_change_lockout` : codes **actuels** faux dans « Changer mon code ».

Règle commune : `MAX_FAILED_ATTEMPTS` essais faux consécutifs → bloqué `LOCK_DURATION`. Un
blocage échu n'est pas réécrit : `lock_end(now)` le lit comme levé, et l'essai faux suivant
repart d'un compteur à zéro (`after_failure`). Une réussite remet à zéro (`LockoutCounter()`).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.domain.shared.business_day import require_aware

MAX_FAILED_ATTEMPTS = 5
LOCK_DURATION = timedelta(minutes=15)


@dataclass(frozen=True, slots=True)
class LockoutCounter:
    failures: int = 0
    locked_until: datetime | None = None

    def __post_init__(self) -> None:
        if isinstance(self.failures, bool) or not isinstance(self.failures, int):
            msg = f"failures doit être un int, reçu {type(self.failures).__name__}"
            raise TypeError(msg)
        if self.failures < 0:
            msg = "Un nombre d'essais faux ne peut pas être négatif"
            raise ValueError(msg)
        if self.locked_until is not None:
            object.__setattr__(self, "locked_until", require_aware(self.locked_until))

    def lock_end(self, now: datetime) -> datetime | None:
        """Fin du blocage s'il court encore à `now`, sinon `None`."""
        if self.locked_until is None:
            return None
        return self.locked_until if require_aware(now) < self.locked_until else None

    def released(self, now: datetime) -> "LockoutCounter":
        """Compteur remis à zéro si son blocage est échu, inchangé sinon."""
        if self.locked_until is not None and self.lock_end(now) is None:
            return LockoutCounter()
        return self

    def after_failure(self, now: datetime, *, can_lock: bool = True) -> "LockoutCounter":
        """Compteur après un essai faux ; bloqué au `MAX_FAILED_ATTEMPTS`ᵉ si `can_lock`.

        Appeler pendant un blocage est une erreur de programmation : l'appelant vérifie
        `lock_end` d'abord et refuse l'essai sans le compter.
        """
        if self.lock_end(now) is not None:
            msg = "Essai compté pendant un blocage : vérifier lock_end() avant"
            raise ValueError(msg)
        failures = self.released(now).failures + 1
        locked = can_lock and failures >= MAX_FAILED_ATTEMPTS
        return LockoutCounter(failures, require_aware(now) + LOCK_DURATION if locked else None)
