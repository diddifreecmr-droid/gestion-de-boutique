"""Réponses du module Ventes (specs § 6.4). Les champs de coût d'une ligne (`frozen_last_cost`,
`frozen_wac`, `margin`, `margin_wac`) ne sont **posés** que pour qui voit les coûts : la route
sérialise avec `response_model_exclude_unset`, la clé est donc absente pour le vendeur
(SEC-N01). Une marge `null` = non calculable (aucun coût connu, RG-T15)."""

from datetime import date, datetime

from pydantic import BaseModel


class DetailResponse(BaseModel):
    color: str | None
    chassis_number: str | None
    engine_number: str | None
    size: str | None


class SaleLineResponse(BaseModel):
    article_id: str
    article_name: str
    sale_mode: str
    quantity: str
    stock_quantity: str
    stock_unit: str
    base_price: int | None
    unit_price: int
    line_total: int
    details: list[DetailResponse]
    frozen_last_cost: int | None = None
    frozen_wac: int | None = None
    margin: int | None = None
    margin_wac: int | None = None


class SalePaymentResponse(BaseModel):
    id: str
    mode_id: str
    amount: int
    reference: str | None
    nature: str


class WarningResponse(BaseModel):
    code: str
    message: str
    details: dict[str, object]


class ReceivableRef(BaseModel):
    """Créance liée (T17) : `id` = celle ouverte par la vente (`GET /receivables/{id}` : reste
    à jour des versements) ; `remaining` = reste à payer de la vente (total - acompte)."""

    id: str
    remaining: int


class CreditResponse(BaseModel):
    reminder_on: date | None
    terms: str | None


class SaleCancellationResponse(BaseModel):
    cancelled_at: datetime
    cancelled_by: str
    reason: str


class ErrorReportResponse(BaseModel):
    id: str
    sale_id: str
    sale_number: str
    description: str
    status: str
    reported_by: str
    reported_at: datetime
    owner_reply: str | None
    replied_at: datetime | None
    version: int


class SaleResponse(BaseModel):
    id: str
    number: str
    provisional_number: str | None
    status: str
    kind: str
    sold_on: date
    sold_at: datetime
    location_id: str
    seller_id: str
    customer_id: str | None
    total: int
    paid: int
    remaining: int
    receivable: ReceivableRef | None
    lines: list[SaleLineResponse]
    payments: list[SalePaymentResponse]
    credit: CreditResponse | None
    note: str | None
    stock_to_verify: bool
    cancellation: SaleCancellationResponse | None
    created_by: str
    device_id: str
    captured_at: datetime
    received_at: datetime
    editable: bool
    version: int
    warnings: list[WarningResponse]
    error_reports: list[ErrorReportResponse]


class SaleTotalsResponse(BaseModel):
    count: int
    total: int
    paid: int


class SalePageResponse(BaseModel):
    items: list[SaleResponse]
    next_cursor: str | None
    first_day: date | None
    last_day: date | None
    totals: SaleTotalsResponse
