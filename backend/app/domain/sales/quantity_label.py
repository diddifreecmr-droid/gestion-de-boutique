"""Quantité d'une ligne telle qu'imprimée sur le reçu (TEX-06, T31) : « 2,5 m », « 1 pièce (5,49 m) ».

- À l'unité : le nombre (« 2 ») ;
- au mètre : la longueur à virgule, sans zéro inutile (« 2,5 m », « 3 m ») ;
- à la pièce : « 1 pièce », « 3 pièces », suivi de la longueur **d'une** pièce quand elle est
  connue (« 1 pièce (5,49 m) »).

Longueur d'une pièce vendue (`sold_piece_length`) : la vente ne garde pas la longueur de la
pièce, seulement le stock retiré (au dixième, QC-3). On imprime la longueur **actuelle** de
l'article si elle redonne exactement ce stock (cas courant : 1 x 5,49 → 5,5 m) ; sinon (la
longueur a été modifiée depuis), la longueur déduite du stock retiré, au centimètre : le reçu
ne contredit jamais ce qui est sorti du stock.
"""

from decimal import ROUND_HALF_UP, Decimal

from app.domain.sales.lines import SaleLine, SaleMode
from app.domain.shared.quantity import TENTH

CENTIMETER = Decimal("0.01")


def length_text(meters: Decimal) -> str:
    """« 2,5 m », « 5,49 m », « 3 m » (virgule décimale, zéros de fin retirés)."""
    text = format(meters.normalize(), "f")
    return f"{text.replace('.', ',')} m"


def _count(quantity: Decimal) -> int:
    if quantity != quantity.to_integral_value():
        msg = f"Nombre de pièces non entier : {quantity}"
        raise ValueError(msg)
    return int(quantity)


def quantity_label(mode: SaleMode, quantity: Decimal, piece_length_m: Decimal | None) -> str:
    if mode is SaleMode.METER:
        return length_text(quantity)
    count = _count(quantity)
    if mode is SaleMode.UNIT:
        return str(count)
    pieces = f"{count} pièce{'s' if count > 1 else ''}"
    return pieces if piece_length_m is None else f"{pieces} ({length_text(piece_length_m)})"


def sold_piece_length(line: SaleLine, current_length_m: Decimal | None) -> Decimal | None:
    """Longueur d'une pièce à imprimer pour une ligne « à la pièce » (`None` sinon)."""
    if line.sale_mode is not SaleMode.PIECE:
        return None
    stock = line.stock_quantity.value
    if current_length_m is not None:
        removed = (line.quantity * current_length_m).quantize(TENTH, rounding=ROUND_HALF_UP)
        if removed == stock:
            return current_length_m
    return (stock / line.quantity).quantize(CENTIMETER, rounding=ROUND_HALF_UP)
