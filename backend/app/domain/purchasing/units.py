"""Unité de saisie d'une ligne d'achat et conversion en unité de stock (CDC § 20.3, RG-X02).

| Unité saisie | Article en | Quantité de stock |
| --- | --- | --- |
| identique à l'unité de stock | Unité, Pièce, Mètre | la quantité saisie |
| Yard | Mètre | `yards_to_meters` : x 0,9144, dixième le plus proche, demi vers le haut |
| Pièce | Mètre (vendu à la pièce) | pièces x longueur de la pièce, même arrondi |

Toute autre combinaison est refusée (`ValidationFailed`, champ `unit`). La quantité saisie est
strictement positive, entière en Unité et Pièce, au dixième en Mètre et Yard (RG-T08) ; la
quantité de stock obtenue l'est aussi (0,04 yard ne fait pas 0 m de stock).
"""

from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from app.domain.shared.errors import ValidationFailed
from app.domain.shared.quantity import TENTH, Quantity, StockUnit, yards_to_meters


class EntryUnit(StrEnum):
    UNIT = "UNIT"
    PIECE = "PIECE"
    METER = "METER"
    YARD = "YARD"

    @property
    def grain(self) -> StockUnit:
        """Précision de la saisie : entière (Unité, Pièce) ou au dixième (Mètre, Yard)."""
        if self in (EntryUnit.METER, EntryUnit.YARD):
            return StockUnit.METER
        return StockUnit(self.value)


def entered_quantity(value: Decimal | int | str, unit: EntryUnit) -> Decimal:
    """Quantité saisie vérifiée (> 0, précision de l'unité) ; `InvalidQuantity` sinon (PUR-04)."""
    return Quantity.of(value, EntryUnit(unit).grain).require_positive("quantity").value


def _incompatible(unit: EntryUnit, stock_unit: StockUnit) -> ValidationFailed:
    msg = "Unité de saisie incompatible avec l'unité de stock de l'article"
    return ValidationFailed(
        msg, details={"field": "unit", "unit": unit.value, "stock_unit": stock_unit.value}
    )


def to_stock_quantity(
    quantity: Decimal,
    unit: EntryUnit,
    stock_unit: StockUnit,
    piece_length_m: Decimal | None = None,
) -> Quantity:
    """Quantité de stock d'une ligne d'achat (RG-X02) : 10 yd → 9,1 m."""
    unit = EntryUnit(unit)
    value = entered_quantity(quantity, unit)
    if unit.value == stock_unit.value:
        return Quantity.of(value, stock_unit)
    if stock_unit is not StockUnit.METER:
        raise _incompatible(unit, stock_unit)
    if unit is EntryUnit.YARD:
        meters = yards_to_meters(value)
    elif unit is EntryUnit.PIECE and piece_length_m is not None:
        product = (value * piece_length_m).quantize(TENTH, rounding=ROUND_HALF_UP)
        meters = Quantity.of(product, StockUnit.METER)
    else:
        raise _incompatible(unit, stock_unit)
    return meters.require_positive("quantity")
