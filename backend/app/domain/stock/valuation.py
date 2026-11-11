"""Valorisation d'une quantité de stock (UC-STK-07 « valeur de l'écart », UC-STK-10).

`quantity x coût unitaire` en FCFA entiers : exact pour une unité entière ; au mètre (dixième),
le produit est **arrondi à l'unité la plus proche, demi vers le haut** (ROUND_HALF_UP, comme
`yards_to_meters`). Un coût inconnu (`None`, article jamais acheté) rend la valeur « non
calculable » (`None`), jamais 0 (RG-T15) : `total_or_none` propage cette inconnue.
"""

from collections.abc import Iterable
from decimal import ROUND_HALF_UP, Decimal

from app.domain.shared.money import Money
from app.domain.shared.quantity import Quantity

_UNIT = Decimal(1)


def value_of(quantity: Quantity, unit_cost: Money | None) -> Money | None:
    """Valeur signée de `quantity` au coût `unit_cost` ; `None` si le coût est inconnu."""
    if unit_cost is None:
        return None
    product = (quantity.value * unit_cost.amount).quantize(_UNIT, rounding=ROUND_HALF_UP)
    return Money(int(product))


def total_or_none(values: Iterable[Money | None]) -> Money | None:
    """Somme ; `None` dès qu'une valeur est inconnue (« non calculable »)."""
    total = Money.zero()
    for value in values:
        if value is None:
            return None
        total += value
    return total
