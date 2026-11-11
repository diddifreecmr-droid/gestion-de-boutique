"""Costing (1/2) : coût unitaire d'un achat et CMP (RG-T10, RG-T12, RG-X02 ; specs § 5.3).

**Règle d'arrondi (décision Q-03)** : les calculs se font en fractions exactes (aucun
flottant) ; un résultat non entier est arrondi **au franc le plus proche, demi vers le haut**
(`round_franc`, montants ≥ 0). Elle s'applique à :

- le total d'une ligne `quantité saisie x prix unitaire` (exact en unités ; au dixième de yard
  ou de mètre, 0,5 franc → 1 franc) ;
- le coût unitaire final `(total de ligne + part des frais) / quantité en unité de stock` ;
- le CMP `(q_stock x CMP + q_achat x coût) / (q_stock + q_achat)` (506 923,08 → 506 923).

Les frais, eux, se répartissent **sans perte** (`Money.allocate` : somme des parts = frais,
reste d'arrondi à la ligne de plus forte valeur). Le total de l'achat est donc la somme exacte
des lignes et des frais ; `q x coût unitaire` peut s'en écarter de `q/2` francs au plus
(SCN-03 c : 3 x 133 333 = 399 999 pour 400 000), écart qui reste dans la valeur du stock.
"""

from collections.abc import Sequence
from decimal import Decimal
from fractions import Fraction
from math import floor

from app.domain.shared.errors import ValidationFailed
from app.domain.shared.money import Money, allocate

_HALF = Fraction(1, 2)


def round_franc(value: Fraction) -> Money:
    """Franc le plus proche, demi vers le haut ; un montant négatif est une erreur d'appelant."""
    if value < 0:
        msg = f"round_franc : montant négatif {value}"
        raise ValueError(msg)
    return Money(floor(value + _HALF))


def _positive(quantity: Decimal, name: str) -> Fraction:
    if not isinstance(quantity, Decimal) or not quantity.is_finite() or quantity <= 0:
        msg = f"{name} doit être un Decimal strictement positif, reçu {quantity!r}"
        raise ValueError(msg)
    return Fraction(quantity)


def line_total(quantity: Decimal, unit_price: Money) -> Money:
    """Total d'une ligne d'achat (UC-ACH-01 étape 3) : quantité saisie x prix de l'unité saisie."""
    unit_price.require_non_negative("unit_price")
    return round_franc(_positive(quantity, "quantity") * unit_price.amount)


def allocate_fees(line_totals: Sequence[Money], fees: Sequence[Money]) -> list[Money]:
    """Part des frais de chaque ligne, au prorata de sa valeur (RG-T10, H6) ; somme exacte.

    Sans frais : parts nulles. Des frais sur un achat dont toutes les lignes valent 0 ne peuvent
    pas se répartir au prorata : `ValidationFailed` (champ `fees`), jamais de répartition
    inventée.
    """
    if not line_totals:
        msg = "allocate_fees : au moins une ligne"
        raise ValueError(msg)
    total = Money.total(fees).require_non_negative("fees")
    if total.amount == 0:
        return [Money.zero() for _ in line_totals]
    if all(line.amount == 0 for line in line_totals):
        msg = "Des frais ne se répartissent pas sur des lignes à 0 FCFA"
        raise ValidationFailed(msg, details={"field": "fees"})
    return allocate(total, [line.amount for line in line_totals])


def final_unit_cost(total: Money, fee_share: Money, stock_quantity: Decimal) -> Money:
    """Coût unitaire final **par unité de stock** (RG-T10 ; RG-X02 : coût au mètre)."""
    cost = Fraction(total.amount + fee_share.amount)
    return round_franc(cost / _positive(stock_quantity, "stock_quantity"))


def next_wac(
    stock_qty: Decimal, current_wac: Money | None, purchase_qty: Decimal, unit_cost: Money
) -> Money:
    """CMP après une entrée coûtée (RG-T12) ; 10 x 500 000 + 5 x 530 000 → 510 000.

    Stock précédent nul, négatif (sortie différée, RG-T18) ou sans coût connu : il ne pèse
    pas, le CMP vaut le coût de l'entrée.
    """
    unit_cost.require_non_negative("unit_cost")
    incoming = _positive(purchase_qty, "purchase_qty")
    if current_wac is None or stock_qty <= 0:
        return unit_cost
    held = Fraction(stock_qty)
    value = held * current_wac.amount + incoming * unit_cost.amount
    return round_franc(value / (held + incoming))
