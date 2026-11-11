"""Corps et réponses des demandes de prix et des retours (T16b ; specs § 6.3, § 6.1).

Requêtes : `id` client idempotent (rejeu → 200), montants entiers FCFA, quantités en chaînes
décimales, champs inconnus refusés (400). Réponses d'un retour : `margin`, `margin_wac` (retour
et lignes) et `cost` (lignes) ne sont **posés** que pour qui voit les coûts (la route
sérialise avec `response_model_exclude_unset` : clés absentes pour le vendeur, SEC-N01).
"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.domain.sales.lines import SaleMode
from app.domain.stock.values import StockCondition
from app.interface.http.schemas.sales import SaleResponse
from app.interface.http.schemas.sales_requests import ID, REF, SaleCreateRequest, _Strict


class PriceRequestCreate(_Strict):
    id: str | None = ID
    article_id: str = REF
    requested_price: int = Field(ge=0)
    sale_mode: SaleMode | None = None
    """« piece » : minimum de la pièce (textile vendu à la pièce)."""


class PriceDecisionRequest(_Strict):
    decision: Literal["accept", "refuse"]
    version: int | None = None


class PriceRequestResponse(BaseModel):
    id: str
    seller_id: str
    article_id: str
    article_name: str
    location_id: str
    requested_price: int
    min_price: int
    status: str
    """Statut effectif : pending, accepted, refused, expired."""
    requested_at: datetime
    expires_at: datetime
    decided_by: str | None
    decided_at: datetime | None
    sale_id: str | None
    version: int


class ReturnLineRequest(_Strict):
    line: int = Field(ge=1, le=50)
    """Position de la ligne dans la vente (1 = première)."""
    quantity: str = Field(max_length=16)
    condition: StockCondition = StockCondition.SELLABLE
    chassis: list[str] = Field(default_factory=list, max_length=100)


class RefundRequest(_Strict):
    amount: int = Field(gt=0)
    mode_id: str = REF
    refunded_on: date | None = None


class ExchangeRequest(_Strict):
    sale: SaleCreateRequest
    """Nouvelle vente : ses `payments` = ce que le client paie en plus de l'avoir."""
    mode_id: str = REF
    """Mode dans lequel l'avoir est remboursé puis versé à la nouvelle vente."""


class SaleReturnCreate(_Strict):
    id: str | None = ID
    lines: list[ReturnLineRequest] = Field(min_length=1, max_length=50)
    reason: str = Field(max_length=500)
    refund: RefundRequest | None = None
    exchange: ExchangeRequest | None = None


class ReturnedLineResponse(BaseModel):
    line: int
    article_id: str
    article_name: str
    quantity: str
    stock_quantity: str
    stock_unit: str
    condition: str
    amount: int
    chassis: list[str]
    cost: int | None = None
    margin: int | None = None
    margin_wac: int | None = None


class RefundResponse(BaseModel):
    amount: int
    mode_id: str
    refunded_on: date


class SaleReturnResponse(BaseModel):
    id: str
    sale_id: str
    sale_number: str
    kind: str
    lines: list[ReturnedLineResponse]
    reason: str
    amount: int
    refund: RefundResponse | None
    credit_reduction: int
    exchange_sale_id: str | None
    returned_at: datetime
    returned_on: date
    created_by: str
    exchange_sale: SaleResponse | None = None
    margin: int | None = None
    margin_wac: int | None = None


class LineBalanceResponse(BaseModel):
    line: int
    article_id: str
    sold: str
    returned: str
    returnable: str


class SaleReturnsResponse(BaseModel):
    sale_id: str
    returns: list[SaleReturnResponse]
    balances: list[LineBalanceResponse]
