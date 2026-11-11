"""Quantités de stock (RG-T08, RG-X02, TR-06).

- `Decimal` exclusivement : un `float` est refusé (`TypeError`), car 0,1 n'y est pas exact.
- Précision : le dixième (0,1). Plus d'une décimale → `InvalidQuantity`, jamais d'arrondi caché.
- `UNIT` et `PIECE` (motos, prêt-à-porter) exigent une valeur entière ; `METER` (textile) admet
  le dixième.
- Comme `Money`, une `Quantity` est **signée** (ajustement négatif, écart d'inventaire) ;
  une saisie se vérifie par `require_positive` / `require_non_negative`.
- Bornes : `NUMERIC(12,1)` (§ 5.1), soit |valeur| < 10¹¹.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from enum import StrEnum
from functools import total_ordering

from app.domain.shared.errors import InvalidQuantity

TENTH = Decimal("0.1")
ONE = Decimal(1)
_LIMIT = Decimal(10) ** 11
METERS_PER_YARD = Decimal("0.9144")  # définition exacte du yard international (RG-X02)


class StockUnit(StrEnum):
    UNIT = "UNIT"
    PIECE = "PIECE"
    METER = "METER"

    @property
    def is_integral(self) -> bool:
        return self is not StockUnit.METER


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, bool | float):
        msg = f"Quantité : {type(value).__name__} refusé, utiliser Decimal, int ou str"
        raise TypeError(msg)
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, str):
        try:
            return Decimal(value.strip())
        except InvalidOperation as exc:
            msg = "Quantité illisible"
            raise InvalidQuantity(msg, details={"value": value[:32]}) from exc
    msg = f"Quantité : type {type(value).__name__} non pris en charge"
    raise TypeError(msg)


@total_ordering
@dataclass(frozen=True, slots=True, eq=False)
class Quantity:
    """Quantité immuable dans une unité de stock. Construire par `Quantity.of(...)`."""

    value: Decimal
    unit: StockUnit

    def __post_init__(self) -> None:
        if not isinstance(self.value, Decimal):
            msg = "Quantity.value doit être un Decimal : utiliser Quantity.of"
            raise TypeError(msg)
        if not isinstance(self.unit, StockUnit):
            msg = f"Unité inconnue : {self.unit!r}"
            raise TypeError(msg)
        details: dict[str, object] = {"value": str(self.value), "unit": self.unit.value}
        if not self.value.is_finite() or abs(self.value) >= _LIMIT:
            msg = "Quantité hors des bornes autorisées"
            raise InvalidQuantity(msg, details=details)
        step = ONE if self.unit.is_integral else TENTH
        if self.value != self.value.quantize(TENTH) or self.value != self.value.quantize(step):
            message = (
                "Quantité entière exigée pour cette unité"
                if self.unit.is_integral
                else "Une quantité au mètre admet au plus une décimale (0,1)"
            )
            raise InvalidQuantity(message, details=details)
        normalized = self.value.quantize(step) if self.value else Decimal(0).quantize(step)
        object.__setattr__(self, "value", normalized)  # forme canonique (« 2.50 » → « 2.5 »)

    @classmethod
    def of(cls, value: Decimal | int | str, unit: StockUnit) -> "Quantity":
        return cls(_to_decimal(value), unit)

    @classmethod
    def zero(cls, unit: StockUnit) -> "Quantity":
        return cls(Decimal(0), unit)

    # ------------------------------------------------------------------ règles
    def require_positive(self, field: str) -> "Quantity":
        if self.value <= 0:
            msg = "La quantité doit être strictement positive"
            raise InvalidQuantity(msg, details={"field": field, "value": str(self.value)})
        return self

    def require_non_negative(self, field: str) -> "Quantity":
        if self.value < 0:
            msg = "La quantité ne peut pas être négative"
            raise InvalidQuantity(msg, details={"field": field, "value": str(self.value)})
        return self

    # ------------------------------------------------------------------ arithmétique
    def _same_unit(self, other: "Quantity") -> None:
        if other.unit is not self.unit:
            msg = f"Unités incompatibles : {self.unit.value} et {other.unit.value}"
            raise ValueError(msg)

    def __add__(self, other: "Quantity") -> "Quantity":
        if not isinstance(other, Quantity):
            return NotImplemented
        self._same_unit(other)
        return Quantity(self.value + other.value, self.unit)

    def __sub__(self, other: "Quantity") -> "Quantity":
        if not isinstance(other, Quantity):
            return NotImplemented
        self._same_unit(other)
        return Quantity(self.value - other.value, self.unit)

    def __neg__(self) -> "Quantity":
        return Quantity(-self.value, self.unit)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Quantity):
            return NotImplemented
        return self.unit is other.unit and self.value == other.value

    def __hash__(self) -> int:
        return hash((self.value, self.unit))

    def __lt__(self, other: "Quantity") -> bool:
        if not isinstance(other, Quantity):
            return NotImplemented
        self._same_unit(other)
        return self.value < other.value

    def __str__(self) -> str:
        """Forme d'échange de l'API (§ 6.1) : chaîne décimale à point, `"2.5"`."""
        return str(self.value)


def yards_to_meters(yards: Decimal | int | str) -> Quantity:
    """Convertit une saisie en yards en mètres (RG-X02 : 1 yard = 0,9144 m).

    La saisie suit la même précision que les quantités (au plus une décimale, ≥ 0). Le produit
    exact est **arrondi au dixième de mètre le plus proche, demi vers le haut**
    (`ROUND_HALF_UP`) : 10 yd → 9,144 m → 9,1 m ; 0,5 yd → 0,4572 m → 0,5 m.
    """
    decimal_yards = _to_decimal(yards)
    entry = Quantity(decimal_yards, StockUnit.METER).require_non_negative("yards")
    meters = (entry.value * METERS_PER_YARD).quantize(TENTH, rounding=ROUND_HALF_UP)
    return Quantity(meters, StockUnit.METER)
