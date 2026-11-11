"""Schémas du stock (`/shops/{id}/stock`, `/adjustments`, `/articles/{id}/movements`, § 6.3).

- Quantités en **chaînes décimales** (`"2.5"`), montants en FCFA entiers (specs § 6.1).
- Champs de coût (`last_cost`, `wac`, `unit_cost`, valeurs) et prix de base : posés **seulement**
  si le rôle peut les voir ; les routes sérialisent sans les champs non posés (clé absente,
  TR-05, SEC-N01). Aucun nom de champ visible du vendeur ne contient « cost », « wac »,
  « value » ni « margin ».
- Valeur « non calculable » (RG-T15) : `null`, accompagné du nombre d'articles sans coût.
"""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ID = Field(max_length=64)
QUANTITY = Field(max_digits=14, decimal_places=3)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class StockColumn(_Strict):
    location_id: str
    name: str
    kind: str
    is_point_of_sale: bool


class StockCell(_Strict):
    location_id: str
    sellable: str
    damaged: str


class StockRow(_Strict):
    article_id: str
    display_name: str
    stock_unit: str
    cells: list[StockCell]
    incoming: str
    """En route vers les lieux affichés (déplacements, Lot 2 : « 0 » au Lot 1)."""
    total: str
    stock_status: Literal["ok", "low", "out"]
    """Pastille : `low` sous le seuil (orange), `out` à zéro (rouge) — stock vendable tous lieux."""
    alert_threshold: str
    base_price: int | None = None
    last_cost: int | None = None
    wac: int | None = None
    wac_value: int | None = None
    """Vendable de la ligne x CMP ; `null` si le CMP est inconnu (« non calculable »)."""


class StockMatrixResponse(_Strict):
    locations: list[StockColumn]
    items: list[StockRow]


class Valuation(_Strict):
    at_wac: int | None
    """Quantité x CMP ; `null` = non calculable (au moins un article sans CMP)."""
    at_wac_known: int
    without_wac: int
    at_last_cost: int | None
    at_last_cost_known: int
    without_last_cost: int


class LocationValuation(_Strict):
    location_id: str
    location_name: str
    active: bool
    sellable: Valuation
    damaged: Valuation
    incoming: Valuation


class StockValueResponse(_Strict):
    locations: list[LocationValuation]
    sellable: Valuation
    """Valeur du stock (CDC § 14.1) : vendable seulement, tous lieux."""
    damaged: Valuation
    incoming: Valuation


class DamagedLine(_Strict):
    article_id: str
    display_name: str
    stock_unit: str
    location_id: str
    location_name: str
    damaged: str
    wac: int | None = None
    wac_value: int | None = None


class DamagedStockResponse(_Strict):
    items: list[DamagedLine]


class MovementDocument(_Strict):
    type: str
    id: str | None
    number: str | None
    """`null` pour une vente vue par le comptable (RG-D03)."""


class MovementResponse(_Strict):
    id: str
    type: str
    type_label: str
    location_id: str
    location_name: str
    condition: str
    quantity: str
    balance_after: str
    document: MovementDocument
    occurred_at: datetime
    recorded_at: datetime
    author_id: str
    stock_to_verify: bool
    reverses_id: str | None
    unit_cost: int | None = None


class MovementListResponse(_Strict):
    article_id: str
    stock_unit: str
    items: list[MovementResponse]
    next_cursor: str | None


class AdjustmentRequest(_Strict):
    id: str | None = Field(default=None, max_length=64)
    location_id: str = ID
    article_id: str = ID
    direction: Literal["in", "out"]
    quantity: Decimal = QUANTITY
    condition: Literal["sellable", "damaged"] = "sellable"
    reason: Literal[
        "breakage",
        "theft",
        "loss",
        "entry_error",
        "sample_or_gift",
        "supplier_return",
        "offcut",
        "other",
    ]
    note: str | None = Field(default=None, max_length=2000)
    photo_id: str | None = Field(default=None, max_length=64)


class AdjustmentResponse(_Strict):
    id: str
    location_id: str
    article_id: str
    direction: str
    quantity: str
    condition: str
    reason: str
    note: str | None
    photo_id: str | None
    inventory_id: str | None
    created_at: datetime
    author_id: str
    balance_after: str | None
    """Stock du lieu après l'ajustement ; `null` pour un rejeu idempotent."""
