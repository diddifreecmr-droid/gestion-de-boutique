"""Réponses du module Créances (specs § 6.3) : montants entiers FCFA, dates ISO, statuts en
codes stables (`open`, `settled`, `cancelled`, `written_off` ; `normal`, `recovery`…)."""

from datetime import date, datetime

from pydantic import BaseModel


class CustomerRef(BaseModel):
    id: str
    name: str
    phone: str


class InstallmentResponse(BaseModel):
    id: str
    number: str
    paid_on: date
    amount: int
    mode_id: str
    reference: str | None
    nature: str
    status: str
    to_refund: bool
    created_by: str
    received_at: datetime
    cancelled_at: datetime | None
    cancelled_by: str | None
    cancel_reason: str | None


class ReminderResponse(BaseModel):
    id: str
    remind_on: date
    note: str | None
    status: str
    alerted_for: date | None


class GuarantorResponse(BaseModel):
    """`id_doc_*` absents (clés omises) hors propriétaire et vendeur responsable (SEC-N06)."""

    id: str
    name: str
    phone: str
    relation: str | None
    id_doc_type: str | None = None
    id_doc_number: str | None = None
    id_doc_photo_id: str | None = None


class WriteOffResponse(BaseModel):
    on: date
    reason: str
    by: str


class ReceivableResponse(BaseModel):
    id: str
    version: int
    customer: CustomerRef
    origin: str
    sale_id: str | None
    sale_number: str | None
    sale_total: int | None
    paid_at_sale: int
    description: str | None
    initial_amount: int
    total_paid: int
    remaining: int
    status: str
    opened_on: date
    seniority_days: int
    seniority_band: str
    last_installment_on: date | None
    responsible_seller_id: str | None
    terms: str | None
    attachment_ids: list[str]
    write_off: WriteOffResponse | None
    cancelled_on: date | None
    manageable: bool
    installments: list[InstallmentResponse]
    reminders: list[ReminderResponse]
    guarantors: list[GuarantorResponse]


class ReceivableSummaryResponse(BaseModel):
    total_due: int
    debtor_count: int
    received_today: int


class ReceivableListResponse(BaseModel):
    summary: ReceivableSummaryResponse
    items: list[ReceivableResponse]


class InstallmentResultResponse(BaseModel):
    installment: InstallmentResponse
    receivable: ReceivableResponse


class InstallmentReceiptResponse(BaseModel):
    shop_name: str
    shop_city: str | None
    shop_phone: str | None
    number: str
    paid_on: date
    customer_name: str
    customer_phone: str
    amount: int
    mode_name: str
    reference: str | None
    nature: str
    cancelled: bool
    total_paid: int
    remaining: int
    settled: bool
    """Mention « Soldé » (reste nul après ce versement)."""
    sale_number: str | None


class StatementLineResponse(BaseModel):
    kind: str
    on: date
    receivable_id: str
    number: str | None
    amount: int
    cancelled: bool
    balance_after: int


class StatementResponse(BaseModel):
    customer: CustomerRef
    total_due: int
    lines: list[StatementLineResponse]
