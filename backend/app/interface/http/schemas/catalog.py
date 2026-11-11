"""Schémas du catalogue (`/shops/{id}/articles`, specs § 6.3).

- Création : `id` (UUIDv7) facultatif fourni par le client → idempotente (même `id` : 200 et
  l'article existant). Champs du profil dans `fields` (codes de `GET /profile`), validés par le
  domaine ; prix facultatifs (propriétaire seul, 403 sinon).
- Modification : `version` obligatoire, champs présents seulement, `reason` facultatif.
- Réponse : les champs de prix et de coût n'apparaissent **que** si le rôle peut les voir
  (clé absente, pas `null` : TR-05, SEC-N01) — les routes sérialisent sans les champs non posés.
- Quantités en chaînes décimales (`"2.5"`), montants en FCFA entiers (specs § 6.1).
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.shared.money import BIGINT_MAX

ID = Field(default=None, max_length=64)
type FieldValue = str | int | bool | None
PRICE = Field(default=None, ge=0, le=BIGINT_MAX)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ArticleCreateRequest(_Strict):
    id: str | None = ID
    fields: dict[str, FieldValue] = Field(default_factory=dict, max_length=32)
    alert_threshold: Decimal | None = Field(default=None, max_digits=13, decimal_places=1)
    photo_id: str | None = ID
    notes: str | None = Field(default=None, max_length=2000)
    base_price: int | None = PRICE
    base_price_piece: int | None = PRICE
    min_price: int | None = PRICE
    min_price_piece: int | None = PRICE


class ArticlePatch(_Strict):
    version: int = Field(ge=1)
    reason: str | None = Field(default=None, max_length=2000)
    fields: dict[str, FieldValue] = Field(default_factory=dict, max_length=32)
    alert_threshold: Decimal | None = Field(default=None, max_digits=13, decimal_places=1)
    photo_id: str | None = ID
    notes: str | None = Field(default=None, max_length=2000)


class PricesRequest(_Strict):
    """`PUT` : les quatre prix remplacés ; un prix absent ou `null` est retiré."""

    version: int = Field(ge=1)
    base_price: int | None = PRICE
    base_price_piece: int | None = PRICE
    min_price: int | None = PRICE
    min_price_piece: int | None = PRICE


class PriceHistoryResponse(_Strict):
    price_kind: str
    old_price: int | None
    new_price: int | None
    effective_at: datetime
    author_id: str


class ArticleResponse(_Strict):
    id: str
    version: int
    status: str
    display_name: str
    brand: str | None
    model: str | None
    reference: str | None
    stock_unit: str
    sold_by_piece: bool
    piece_length_m: str | None
    attributes: dict[str, FieldValue]
    alert_threshold: str | None
    effective_alert_threshold: str
    """Seuil appliqué : celui de l'article, sinon le réglage de la boutique."""
    photo_id: str | None
    notes: str | None
    created_at: datetime
    # Prix de vente (SELLING_PRICE_READ) ; minimum selon `visibility.py`.
    base_price: int | None = None
    base_price_piece: int | None = None
    min_price: int | None = None
    min_price_piece: int | None = None
    min_price_active: bool | None = None
    """Vrai si le réglage « prix minimum » de la boutique est activé (H9)."""
    # Coûts calculés par les achats (COST_READ) : jamais pour le vendeur (RG-D02).
    last_cost: int | None = None
    wac: int | None = None
    price_history: list[PriceHistoryResponse] | None = None
    """Fiche article seulement, pour qui voit l'historique des prix (propriétaire)."""


class ArticleListResponse(_Strict):
    items: list[ArticleResponse]
    next_cursor: str | None
