"""Schémas des tissus textiles (`/shops/{id}/articles/fabrics`, décision client du 2026-11-15).

Un tissu = un article par couleur (« Djampar — Rouge »). Prix en FCFA entiers : `base_price` /
`min_price` au **mètre**, `base_price_piece` / `min_price_piece` au **rouleau** (code interne
« pièce ») ; `roll_length_m` = longueur d'un rouleau (exigée sauf `meter_only`). Réponse : les
articles des couleurs, présentés comme la liste du catalogue (droits de l'acteur, TR-05).
"""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.shared.money import BIGINT_MAX
from app.interface.http.schemas.catalog import ArticleResponse

PRICE = Field(default=None, ge=0, le=BIGINT_MAX)
COLORS = Field(min_length=1, max_length=50)
LENGTH = Field(default=None, gt=0, max_digits=8, decimal_places=2)
THRESHOLD = Field(default=None, max_digits=13, decimal_places=1)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class FabricPrices(_Strict):
    base_price: int | None = PRICE
    base_price_piece: int | None = PRICE
    min_price: int | None = PRICE
    min_price_piece: int | None = PRICE


class FabricCreateRequest(FabricPrices):
    fabric: str = Field(min_length=1, max_length=60)
    colors: list[str] = COLORS
    roll_length_m: Decimal | None = LENGTH
    meter_only: bool = False
    """Vendu au mètre seulement (ex. Getzner) : aucun prix ni vente au rouleau."""
    alert_threshold: Decimal | None = THRESHOLD


class FabricPatch(_Strict):
    """Champs présents seulement (`null` efface) ; s'applique à toutes les couleurs."""

    roll_length_m: Decimal | None = LENGTH
    meter_only: bool | None = None
    alert_threshold: Decimal | None = THRESHOLD
    prices: FabricPrices | None = None
    """Les quatre prix remplacés pour chaque couleur ; absent = inchangés."""


class FabricColorsRequest(_Strict):
    colors: list[str] = COLORS


class FabricResponse(_Strict):
    fabric: str
    items: list[ArticleResponse]
