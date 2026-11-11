"""Identifiants typés en UUIDv7 (specs D5, § 5.1, TR-11).

Python 3.12 ne fournit pas `uuid.uuid7` : `Uuid7Generator` l'implémente selon la RFC 9562 § 5.7
(48 bits d'horodatage Unix en ms | version 7 | 12 bits `rand_a` | variante `10` | 62 bits `rand_b`).

Monotonie (RFC 9562 § 6.2, méthode 2) : les 74 bits aléatoires forment un compteur. Dans la même
milliseconde — ou si l'horloge recule — on reprend l'horodatage précédent et on incrémente ce
compteur ; à sa saturation, l'horodatage avance d'une ms. Le bit de poids fort du compteur est
mis à 0 à chaque nouvelle ms pour laisser de la marge. Les identifiants d'un même processus sont
donc **strictement croissants**. L'aléa vient de `secrets` (cryptographiquement sûr).
"""

import secrets
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Self
from uuid import UUID

from app.domain.shared.errors import InvalidIdentifier

_RANDOM_BITS = 74
_COUNTER_MAX = (1 << _RANDOM_BITS) - 1
_TIMESTAMP_MAX = (1 << 48) - 1
_RFC_VARIANT = 0b10


def _clock_ms() -> int:
    return time.time_ns() // 1_000_000


class Uuid7Generator:
    """Générateur UUIDv7 monotone, sûr entre threads ; horloge et aléa injectables (tests)."""

    def __init__(
        self,
        clock_ms: Callable[[], int] = _clock_ms,
        randbits: Callable[[int], int] = secrets.randbits,
    ) -> None:
        self._clock_ms = clock_ms
        self._randbits = randbits
        self._lock = threading.Lock()
        self._last_ms = -1
        self._counter = 0

    def __call__(self) -> UUID:
        with self._lock:
            now = self._clock_ms()
            if now > self._last_ms:
                self._last_ms = now
                self._counter = self._randbits(_RANDOM_BITS - 1)  # bit de tête à 0 : marge
            elif self._counter < _COUNTER_MAX:
                self._counter += 1
            else:
                self._last_ms += 1
                self._counter = self._randbits(_RANDOM_BITS - 1)
            return build_uuid7(self._last_ms, self._counter)


def build_uuid7(timestamp_ms: int, random74: int) -> UUID:
    """Assemble les champs RFC 9562 ; lève `ValueError` si un champ déborde."""
    if not 0 <= timestamp_ms <= _TIMESTAMP_MAX:
        msg = f"Horodatage UUIDv7 hors de 48 bits : {timestamp_ms}"
        raise ValueError(msg)
    if not 0 <= random74 <= _COUNTER_MAX:
        msg = "La partie aléatoire d'un UUIDv7 doit tenir sur 74 bits"
        raise ValueError(msg)
    rand_a = random74 >> 62
    rand_b = random74 & ((1 << 62) - 1)
    value = (timestamp_ms << 80) | (0x7 << 76) | (rand_a << 64) | (_RFC_VARIANT << 62) | rand_b
    return UUID(int=value)


uuid7 = Uuid7Generator()
"""Générateur par défaut du processus."""


def uuid7_timestamp_ms(value: UUID) -> int:
    return value.int >> 80


def is_uuid7(value: UUID) -> bool:
    return value.version == 7 and (value.int >> 62) & 0b11 == _RFC_VARIANT


@dataclass(frozen=True, order=True, slots=True)
class EntityId:
    """Base des identifiants typés : `class SaleId(EntityId)` suffit à créer un nouveau type.

    Deux identifiants de types différents ne sont jamais égaux, même à valeur identique. La
    valeur doit être un UUIDv7 (variante RFC) ; toute autre forme est refusée.
    """

    value: UUID

    def __post_init__(self) -> None:
        if type(self) is EntityId:
            msg = "EntityId est abstraite : utiliser un identifiant typé (ShopId, UserId…)"
            raise TypeError(msg)
        if not isinstance(self.value, UUID):
            msg = f"{type(self).__name__}.value doit être un UUID, reçu {type(self.value)}"
            raise TypeError(msg)
        if not is_uuid7(self.value):
            msg = "Identifiant attendu au format UUIDv7"
            raise InvalidIdentifier(
                msg, details={"type": type(self).__name__, "value": str(self.value)}
            )

    @classmethod
    def new(cls) -> Self:
        return cls(uuid7())

    @classmethod
    def parse(cls, text: str) -> Self:
        """Lit la forme canonique `xxxxxxxx-xxxx-7xxx-…` (casse indifférente)."""
        try:
            value = UUID(text)
        except (ValueError, TypeError, AttributeError) as exc:
            msg = "Identifiant illisible"
            raise InvalidIdentifier(
                msg, details={"type": cls.__name__, "value": str(text)[:64]}
            ) from exc
        return cls(value)

    @property
    def timestamp_ms(self) -> int:
        return uuid7_timestamp_ms(self.value)

    def __str__(self) -> str:
        return str(self.value)


class ShopId(EntityId):
    """Boutique (tenant)."""

    __slots__ = ()


class UserId(EntityId):
    """Utilisateur (acteur)."""

    __slots__ = ()


class DeviceId(EntityId):
    """Appareil enregistré (en-tête `X-Device-Id`)."""

    __slots__ = ()


class EventId(EntityId):
    """Événement de domaine."""

    __slots__ = ()
