"""Montants en FCFA entiers (H2, RG-T07, TR-06).

Choix de conception : **un seul type `Money`, signé**.

- Un montant *calculé* (marge, écart d'inventaire, solde) peut être négatif : `Money(-1500)`.
- Un montant *de saisie* (prix, versement, frais) ne l'est jamais (RG-T07) : il se construit par
  `Money.entry(valeur, champ)` ou se vérifie par `require_non_negative(champ)`, qui lèvent
  `InvalidAmount` avec le nom du champ dans `details`.

Un seul type évite la cascade de conversions dans les calculs (prix - coût = marge) ; la règle de
signe est appliquée aux frontières, là où une saisie entre dans le domaine.

Une valeur non entière (float, Decimal, bool, str) est une **erreur de programmation** :
`TypeError`, jamais d'arrondi silencieux. Les bornes sont celles d'un `BIGINT` (§ 5.1).
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from math import floor

from app.domain.shared.errors import InvalidAmount

BIGINT_MAX = 2**63 - 1
BIGINT_MIN = -(2**63)


def _require_int(value: object, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{what} doit être un int (FCFA entiers), reçu {type(value).__name__}"
        raise TypeError(msg)
    return value


@dataclass(frozen=True, order=True, slots=True)
class Money:
    """Montant signé en FCFA entiers, immuable."""

    amount: int

    def __post_init__(self) -> None:
        _require_int(self.amount, "Money.amount")
        if not BIGINT_MIN <= self.amount <= BIGINT_MAX:
            msg = "Montant hors des bornes autorisées"
            raise InvalidAmount(msg, details={"amount": str(self.amount)})

    # ------------------------------------------------------------------ fabriques
    @classmethod
    def zero(cls) -> "Money":
        return cls(0)

    @classmethod
    def entry(cls, amount: int, field: str) -> "Money":
        """Montant saisi par un utilisateur : jamais négatif (RG-T07)."""
        return cls(amount).require_non_negative(field)

    @classmethod
    def total(cls, amounts: Iterable["Money"]) -> "Money":
        """Somme d'un itérable de `Money` (vide → zéro)."""
        result = 0
        for item in amounts:
            if not isinstance(item, Money):
                msg = f"Money.total n'additionne que des Money, reçu {type(item).__name__}"
                raise TypeError(msg)
            result += item.amount
        return cls(result)

    # ------------------------------------------------------------------ règles
    @property
    def is_negative(self) -> bool:
        return self.amount < 0

    def require_non_negative(self, field: str) -> "Money":
        """Renvoie `self` ou lève `InvalidAmount` (RG-T07) en nommant le champ fautif."""
        if self.amount < 0:
            msg = "Un montant saisi ne peut pas être négatif"
            raise InvalidAmount(msg, details={"field": field, "amount": self.amount})
        return self

    # ------------------------------------------------------------------ arithmétique
    def __add__(self, other: "Money") -> "Money":
        if not isinstance(other, Money):
            return NotImplemented
        return Money(self.amount + other.amount)

    def __sub__(self, other: "Money") -> "Money":
        if not isinstance(other, Money):
            return NotImplemented
        return Money(self.amount - other.amount)

    def __neg__(self) -> "Money":
        return Money(-self.amount)

    def __mul__(self, factor: int) -> "Money":
        if isinstance(factor, bool) or not isinstance(factor, int):
            return NotImplemented
        return Money(self.amount * factor)

    __rmul__ = __mul__

    def __str__(self) -> str:
        """Affichage RG-T07 : espace entre milliers, `1 250 000 FCFA`."""
        return f"{self.amount:,} FCFA".replace(",", " ")


Weight = int | Decimal


def _weight(value: object) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, int | Decimal):
        msg = f"Un poids doit être int ou Decimal, reçu {type(value).__name__}"
        raise TypeError(msg)
    if isinstance(value, Decimal) and not value.is_finite():
        msg = "Poids de répartition non fini"
        raise InvalidAmount(msg, details={"weight": str(value)})
    if value < 0:
        msg = "Poids de répartition négatif"
        raise InvalidAmount(msg, details={"weight": str(value)})
    return Fraction(value)


def allocate(total: Money, weights: Sequence[Weight]) -> list[Money]:
    """Répartit `total` au prorata de `weights`, de façon **exacte** (RG-T10, specs § 5.3).

    Chaque part vaut `⌊total * poids / Σ poids⌋` (calcul en fractions exactes, aucun flottant) ;
    le reste de l'arrondi (strictement inférieur au nombre de parts) va **en entier** à la part
    de plus fort poids (la première en cas d'égalité). Garanties : somme des parts = `total`,
    parts ≥ 0, poids nul → part nulle.

    `total` doit être ≥ 0 (frais saisis) ; il faut au moins un poids et une somme de poids > 0.
    Les poids sont typiquement `quantité * prix` (Decimal au dixième pour le mètre).
    """
    if not isinstance(total, Money):
        msg = f"allocate attend un Money, reçu {type(total).__name__}"
        raise TypeError(msg)
    total.require_non_negative("total")
    fractions = [_weight(w) for w in weights]
    weight_sum = sum(fractions, Fraction(0))
    if weight_sum == 0:
        msg = "Répartition impossible : aucun poids positif"
        raise InvalidAmount(msg, details={"parts": len(fractions)})
    shares = [floor(total.amount * w / weight_sum) for w in fractions]
    heaviest = max(range(len(fractions)), key=lambda i: (fractions[i], -i))
    shares[heaviest] += total.amount - sum(shares)
    return [Money(share) for share in shares]
