"""Stock d'un tissu en rouleaux entiers + reste (décision client du 2026-11-15, Textile).

« 7 rouleaux + 12 m » : le stock (en mètres, au dixième) est découpé en rouleaux entiers de la
longueur du tissu et le reste du rouleau entamé. Affichage seulement : le stock reste tenu en
mètres. Stock négatif (vente jamais refusée, « Stock à vérifier ») : pas de découpage (`None`),
le chiffre en mètres seul fait foi.
"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class RollSplit:
    rolls: int
    meters_rest: Decimal


def split_rolls(meters: Decimal, roll_length_m: Decimal) -> RollSplit | None:
    if roll_length_m <= 0:
        msg = f"Longueur de rouleau strictement positive attendue, reçu {roll_length_m}"
        raise ValueError(msg)
    if meters < 0:
        return None
    rolls = int(meters // roll_length_m)
    return RollSplit(rolls, meters - rolls * roll_length_m)
