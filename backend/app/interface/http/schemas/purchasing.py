"""Schémas du module Achats (specs § 6.3, § 6.1) : `id` client idempotent (rejeu → 200),
montants entiers FCFA, quantités en chaînes décimales (`"9.1"`), `PATCH` + `version` + `reason`.
Coûts servis au seul propriétaire et au comptable (vendeur et chauffeur : 403, RG-D02).
"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.purchasing.lines import FeeKind
from app.domain.purchasing.units import EntryUnit

ID = Field(default=None, max_length=64)
REF = Field(max_length=64)
TEXT = Field(default=None, max_length=500)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LineRequest(_Strict):
    article_id: str = REF
    quantity: str = Field(max_length=16)
    unit: EntryUnit | None = None
    """Unité saisie (UNIT, PIECE, METER, YARD) ; absente : unité de stock de l'article."""
    unit_price: int


class FeeRequest(_Strict):
    kind: FeeKind
    amount: int
    label: str | None = Field(default=None, max_length=120)


class PurchaseCreateRequest(_Strict):
    id: str | None = ID
    lines: list[LineRequest] = Field(min_length=1, max_length=100)
    fees: list[FeeRequest] = Field(default_factory=list, max_length=20)
    purchase_date: date | None = None
    location_id: str | None = ID
    """Absent : lieu de réception par défaut (réglage de la boutique, Q-01)."""
    supplier_id: str | None = ID
    invoice_ref: str | None = Field(default=None, max_length=64)
    invoice_photo_id: str | None = ID
    note: str | None = TEXT
    confirm_price_gap: bool = False
    """Vrai après l'avertissement `PRICE_GAP_CONFIRMATION_REQUIRED` (écart > 30 %)."""


class PurchasePatch(_Strict):
    version: int
    reason: str = Field(max_length=500)
    lines: list[LineRequest] | None = Field(default=None, min_length=1, max_length=100)
    fees: list[FeeRequest] | None = Field(default=None, max_length=20)
    purchase_date: date | None = None
    location_id: str | None = ID
    supplier_id: str | None = ID
    invoice_ref: str | None = Field(default=None, max_length=64)
    invoice_photo_id: str | None = ID
    note: str | None = TEXT
    confirm_price_gap: bool = False


class PurchaseCancelRequest(_Strict):
    reason: str = Field(max_length=500)


class PaymentRequest(_Strict):
    id: str | None = ID
    amount: int
    mode_id: str = REF
    paid_on: date | None = None
    reference: str | None = Field(default=None, max_length=64)


class LineResponse(_Strict):
    article_id: str
    quantity: str
    unit: str
    stock_quantity: str
    stock_unit: str
    unit_price: int
    total: int
    fee_share: int
    final_unit_cost: int


class FeeResponse(_Strict):
    kind: str
    label: str | None
    amount: int


class PaymentResponse(_Strict):
    id: str
    paid_on: date
    amount: int
    mode_id: str
    reference: str | None
    recorded_at: datetime
    recorded_by: str


class PurchaseCancellationResponse(_Strict):
    cancelled_at: datetime
    cancelled_by: str
    reason: str


class PurchaseResponse(_Strict):
    id: str
    number: str
    supplier_id: str | None
    purchase_date: date
    location_id: str
    invoice_ref: str | None
    invoice_photo_id: str | None
    note: str | None
    lines: list[LineResponse]
    fees: list[FeeResponse]
    article_count: int
    merchandise_total: int
    fees_total: int
    total: int
    paid: int
    payment_status: str
    """`to_pay`, `partially_paid` ou `paid` (UC-ACH-06) ; `status` : `valid` ou `cancelled`."""
    payments: list[PaymentResponse]
    status: str
    cancellation: PurchaseCancellationResponse | None
    created_by: str
    device_id: str
    captured_at: datetime
    received_at: datetime
    editable: bool
    cancellable: bool
    last_correction_day: date
    """Dernier jour de correction pour le comptable (J+7 après la date d'achat)."""
    version: int


class PurchaseTotalsResponse(_Strict):
    count: int
    merchandise: int
    fees: int
    total: int
    paid: int


class PurchasePageResponse(_Strict):
    items: list[PurchaseResponse]
    next_cursor: str | None
    first_day: date
    last_day: date
    totals: PurchaseTotalsResponse
    """Achats valides de toute la période filtrée (annulés exclus, RG-T03)."""


class SupplierRequest(_Strict):
    id: str | None = ID
    name: str = Field(max_length=120)
    phone: str | None = Field(default=None, max_length=120)
    city: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, max_length=120)
    note: str | None = TEXT


class SupplierPatch(_Strict):
    version: int
    name: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=120)
    city: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, max_length=120)
    note: str | None = TEXT
    active: bool | None = None


class SupplierResponse(_Strict):
    id: str
    name: str
    phone: str | None
    city: str | None
    country: str | None
    note: str | None
    active: bool
    version: int


class SupplierListResponse(_Strict):
    items: list[SupplierResponse]


class SupplierSheetResponse(_Strict):
    supplier: SupplierResponse
    first_day: date
    last_day: date
    totals: PurchaseTotalsResponse
    """Total acheté sur la période (achats valides)."""
    purchases: list[PurchaseResponse]
