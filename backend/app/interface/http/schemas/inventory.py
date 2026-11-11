"""Schémas des inventaires (`/shops/{id}/inventories`, UC-STK-07).

Pendant le comptage, une ligne ne porte **que** la quantité comptée : `theoretical`,
`difference` et `gap_value` sont absents du JSON (clé non posée, INV-01) ; ils apparaissent à
la validation. `gap_value` (écart x CMP) n'est posé que pour qui voit les coûts ; `null` =
non calculable (CMP inconnu).
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

ID = Field(max_length=64)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class InventoryStartRequest(_Strict):
    id: str | None = Field(default=None, max_length=64)
    location_id: str = ID


class CountEntry(_Strict):
    article_id: str = ID
    counted: Decimal | None = Field(max_digits=14, decimal_places=3)
    """`null` efface un comptage déjà saisi."""


class CountsRequest(_Strict):
    version: int = Field(ge=1)
    counts: list[CountEntry] = Field(max_length=5000)


class ReasonEntry(_Strict):
    article_id: str = ID
    reason: str = Field(max_length=2000)


class ValidateRequest(_Strict):
    version: int = Field(ge=1)
    reasons: list[ReasonEntry] = Field(default_factory=list, max_length=5000)
    global_reason: str | None = Field(default=None, max_length=2000)


class AbandonRequest(_Strict):
    version: int = Field(ge=1)


class InventoryLineResponse(_Strict):
    article_id: str
    display_name: str
    stock_unit: str
    counted: str | None
    theoretical: str | None = None
    difference: str | None = None
    reason: str | None = None
    gap_value: int | None = None


class InventoryResponse(_Strict):
    id: str
    number: str
    version: int
    status: str
    location_id: str
    location_name: str
    started_at: datetime
    closed_at: datetime | None
    global_reason: str | None
    sales_since_start: int
    """Ventes enregistrées au lieu depuis le début du comptage (en cours seulement)."""
    sales_message: str | None
    """« 2 ventes enregistrées depuis le début du comptage », ou `null`."""
    counted_lines: int
    lines: list[InventoryLineResponse]
    gap_count: int | None = None
    gap_value: int | None = None
