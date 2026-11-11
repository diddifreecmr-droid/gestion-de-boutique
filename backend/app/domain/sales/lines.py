"""Ligne de vente et détails vendus (CDC § 20.4 ; RG-T13, RG-T14, RG-T15, RG-M03).

- Mode de vente : À l'unité (motos, prêt-à-porter), Au mètre et À la pièce (textile).
- `stock_quantity` : quantité retirée du stock, dans l'unité de stock (pièces x longueur de la
  pièce pour le textile vendu à la pièce, RG-X02) ; calculée par l'application.
- **Instantanés** : nom de l'article et prix de base du jour (`article_name_snapshot`,
  `base_price_snapshot`) ; **coûts figés** (`frozen_last_cost`, `frozen_wac`) lus sur l'article
  dans la transaction de la vente : ils ne changent plus jamais (RG-T13, H5).
- **Arrondi (point T04 tranché)** : total de ligne = quantité x prix unitaire, **arrondi au
  franc, demi vers le haut** (`ROUND_HALF_UP`) ; exact pour l'unité et la pièce (quantité
  entière), utile au mètre (2,5 m x 1 001 = 2 502,5 → 2 503). Le coût d'une ligne suit la
  même règle (coût par unité de stock x quantité de stock).
- **Marges** (RG-T14) : `margin` = total de ligne - dernier coût figé x quantité de stock ;
  `margin_wac` = idem au CMP figé. Pour l'unité : (prix - coût) x quantité. Coût inconnu →
  marge **non calculable** (`None`, RG-T15) ; une marge peut être négative.
- Détails vendus : une entrée par unité (couleur, châssis, moteur, taille), au plus la quantité
  vendue (une seule pour une ligne au mètre).
"""

from dataclasses import dataclass, replace
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from app.domain.catalog.ids import ArticleId
from app.domain.sales.chassis import CHASSIS_MAX_LENGTH, chassis_key
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.money import Money
from app.domain.shared.quantity import Quantity
from app.domain.shops.values import clean_optional, clean_text

DETAIL_MAX_LENGTH = 64


class SaleMode(StrEnum):
    UNIT = "unit"  # À l'unité
    METER = "meter"  # Au mètre
    PIECE = "piece"  # À la pièce


def round_franc(value: Decimal) -> Money:
    """Arrondi au franc le plus proche, demi vers le haut."""
    return Money(int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP)))


@dataclass(frozen=True, slots=True, kw_only=True)
class SoldDetail:
    color: str | None = None
    chassis_number: str | None = None
    engine_number: str | None = None
    size: str | None = None

    def __post_init__(self) -> None:
        for name in ("color", "engine_number", "size"):
            value = clean_optional(getattr(self, name), name, max_length=DETAIL_MAX_LENGTH)
            object.__setattr__(self, name, value)
        if self.chassis_number is not None and self.chassis_number.strip():
            chassis = clean_text(
                self.chassis_number, "chassis_number", max_length=CHASSIS_MAX_LENGTH
            )
            chassis_key(chassis)  # au moins une lettre ou un chiffre
            object.__setattr__(self, "chassis_number", chassis)
        else:
            object.__setattr__(self, "chassis_number", None)

    @property
    def chassis_key(self) -> str | None:
        return None if self.chassis_number is None else chassis_key(self.chassis_number)

    def filled(self) -> dict[str, str]:
        """Champs renseignés (contrôle contre les champs de vente du profil)."""
        values = {
            "color": self.color,
            "chassis_number": self.chassis_number,
            "engine_number": self.engine_number,
            "size": self.size,
        }
        return {name: value for name, value in values.items() if value is not None}


@dataclass(frozen=True, slots=True, kw_only=True)
class SaleLine:
    article_id: ArticleId
    article_name: str
    sale_mode: SaleMode
    quantity: Decimal
    stock_quantity: Quantity
    unit_price: Money
    base_price: Money | None = None
    frozen_last_cost: Money | None = None
    frozen_wac: Money | None = None
    details: tuple[SoldDetail, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.article_id, ArticleId):
            msg = "SaleLine.article_id doit être un ArticleId"
            raise TypeError(msg)
        object.__setattr__(self, "sale_mode", SaleMode(self.sale_mode))
        self.unit_price.require_non_negative("lines.unit_price")
        self.stock_quantity.require_positive("lines.quantity")
        details = tuple(self.details)
        allowed = 1 if self.sale_mode is SaleMode.METER else int(self.quantity)
        if len(details) > allowed:
            msg = "Plus de détails que d'unités vendues"
            raise ValidationFailed(msg, details={"field": "lines.details", "max": allowed})
        object.__setattr__(self, "details", details)

    @property
    def line_total(self) -> Money:
        return round_franc(self.quantity * self.unit_price.amount)

    def _margin(self, cost: Money | None) -> Money | None:
        if cost is None:
            return None
        return self.line_total - round_franc(self.stock_quantity.value * cost.amount)

    @property
    def margin(self) -> Money | None:
        return self._margin(self.frozen_last_cost)

    @property
    def margin_wac(self) -> Money | None:
        return self._margin(self.frozen_wac)

    @property
    def below_base(self) -> bool:
        return self.base_price is not None and self.unit_price < self.base_price

    def repriced(self, unit_price: Money) -> "SaleLine":
        """Même ligne à un autre prix, **mêmes coûts figés** (UC-VEN-07)."""
        return replace(self, unit_price=unit_price)

    def with_details(self, details: tuple[SoldDetail, ...]) -> "SaleLine":
        return replace(self, details=details)
