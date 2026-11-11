"""Corps et réponses de `POST /sync` et `GET /offline-snapshot` (specs § 6.5, T23).

`payload` d'une opération : le corps de `POST /sales` (`sale.create`) ou de `POST /expenses`
(`expense.create`), validé **par opération** (un payload invalide refuse cette opération
seulement, `VALIDATION_ERROR` + `details.fields`). Son `id` éventuel doit valoir `op_id`.
L'instantané ne porte **aucun** coût (clés absentes du schéma, SEC-N01).
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.application.sync.inputs import MAX_OPERATIONS
from app.interface.http.schemas.customers import CustomerResponse
from app.interface.http.schemas.expenses import ExpenseCategoryResponse
from app.interface.http.schemas.places import LocationResponse, PaymentModeResponse


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SyncOperationRequest(_Strict):
    op_id: str = Field(max_length=64)
    type: str = Field(max_length=32)
    """`sale.create`, `expense.create` ; `trip_step.create` / `trip_expense.create` : Lot 2."""
    provisional_number: str | None = Field(default=None, max_length=32)
    """`V-HL-3F2A-0007` : 4 derniers chiffres hexadécimaux du `device_id` (RG-T06)."""
    captured_at: AwareDatetime
    """Heure de la saisie sur l'appareil (H12), avec fuseau."""
    payload: dict[str, Any] = Field(default_factory=dict)


class SyncRequest(_Strict):
    device_id: str = Field(max_length=64)
    operations: list[SyncOperationRequest] = Field(max_length=MAX_OPERATIONS)


class SyncNoticeResponse(BaseModel):
    code: str
    message: str
    details: dict[str, Any]


class SyncResultResponse(BaseModel):
    op_id: str
    status: Literal["accepted", "duplicate", "rejected"]
    provisional_number: str | None
    number: str | None
    """Numéro définitif (`V-000125`) ; `null` si l'opération est refusée."""
    entity_id: str | None
    warnings: list[SyncNoticeResponse]
    error: SyncNoticeResponse | None


class SyncResponse(BaseModel):
    results: list[SyncResultResponse]
    """Un résultat par opération, dans l'ordre reçu."""


class SnapshotArticleResponse(BaseModel):
    id: str
    display_name: str
    reference: str | None
    stock_unit: str
    sold_by_piece: bool
    base_price: int | None
    base_price_piece: int | None
    min_price: int | None
    """`null` aussi quand le rôle ne voit pas le prix minimum (`CatalogVisibility`)."""
    min_price_piece: int | None


class OfflineSnapshotResponse(BaseModel):
    generated_at: datetime
    since: datetime | None
    full: bool
    """Toujours vrai au Lot 1 : instantané complet, `since` n'est pas encore exploité."""
    min_price_enabled: bool
    articles: list[SnapshotArticleResponse]
    customers: list[CustomerResponse]
    expense_categories: list[ExpenseCategoryResponse]
    locations: list[LocationResponse]
    payment_modes: list[PaymentModeResponse]
