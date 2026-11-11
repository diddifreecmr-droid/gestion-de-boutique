"""Ligne d'inventaire (CDC § 20.2 « Ligne d'inventaire ») et résultat de validation.

- `counted` : saisi pendant le comptage (`None` = pas encore compté) ; ≥ 0.
- `theoretical` : stock **vendable** du lieu, figé **à la validation** (décision Q-17 : les
  ventes faites pendant le comptage sont déjà sorties du théorique ; l'écran le signale par
  « N ventes enregistrées depuis le début du comptage »). Masqué tant que l'inventaire est en
  cours : il vaut `None` jusque-là, il n'existe donc nulle part à renvoyer.
- `difference = counted - theoretical` ; `gap_value = difference x CMP` (`None` si le CMP est
  inconnu) ; `reason` : motif de l'écart (obligatoire si l'écart est non nul, sauf motif global).
- Le stock abîmé n'est pas inventorié ici (il se traite par l'écran « Stock abîmé »).
"""

from dataclasses import dataclass, replace

from app.domain.catalog.ids import ArticleId
from app.domain.shared.money import Money
from app.domain.shared.quantity import Quantity, StockUnit
from app.domain.stock.valuation import value_of


@dataclass(frozen=True, slots=True)
class LineCheck:
    """Ce que la validation lit pour une ligne : stock vendable du lieu et CMP de l'article."""

    theoretical: Quantity
    wac: Money | None


@dataclass(frozen=True, slots=True, kw_only=True)
class InventoryLine:
    article_id: ArticleId
    unit: StockUnit
    counted: Quantity | None = None
    theoretical: Quantity | None = None
    reason: str | None = None
    gap_value: Money | None = None

    def __post_init__(self) -> None:
        for quantity in (self.counted, self.theoretical):
            if quantity is not None and quantity.unit is not self.unit:
                msg = "InventoryLine : quantité dans une autre unité que l'article"
                raise ValueError(msg)
        if self.counted is not None:
            self.counted.require_non_negative("counted")

    @property
    def difference(self) -> Quantity | None:
        if self.counted is None or self.theoretical is None:
            return None
        return self.counted - self.theoretical

    @property
    def has_gap(self) -> bool:
        difference = self.difference
        return difference is not None and difference.value != 0

    def count(self, counted: Quantity | None) -> "InventoryLine":
        return replace(self, counted=counted)

    def settle(self, check: LineCheck, reason: str | None) -> "InventoryLine":
        """Ligne validée : théorique figé, valeur de l'écart, motif (si écart)."""
        settled = replace(self, theoretical=check.theoretical)
        difference = settled.difference
        if difference is None:  # exclu par l'agrégat (toutes les lignes sont comptées)
            msg = "Ligne non comptée à la validation"
            raise ValueError(msg)
        if difference.value == 0:
            return replace(settled, reason=None, gap_value=Money.zero())
        return replace(settled, reason=reason, gap_value=value_of(difference, check.wac))
