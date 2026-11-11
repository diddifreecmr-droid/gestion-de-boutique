"""Corps de requête du module Créances (specs § 6.3, § 6.1) : `id` client idempotent (rejeu →
200), montants entiers FCFA, dates ISO, `PATCH` + `version`. Champs inconnus refusés (400)."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.domain.receivables.follow_up import ReminderStatus
from app.domain.sales.customer import IdDocumentType
from app.interface.http.schemas.sales_requests import SaleCustomerRequest

ID = Field(default=None, max_length=64)
REF = Field(max_length=64)
TEXT = Field(default=None, max_length=500)
SHORT = Field(default=None, max_length=64)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LegacyReceivableRequest(_Strict):
    """UC-CRE-02 : client existant (`customer.id`) ou nom + téléphone."""

    id: str | None = ID
    customer: SaleCustomerRequest
    amount: int
    opened_on: date
    description: str = Field(max_length=500)
    responsible_seller_id: str | None = ID
    terms: str | None = TEXT


class ReceivablePatch(_Strict):
    """Champs présents seulement ; `responsible_seller_id` : propriétaire seul (Q-21)."""

    version: int
    responsible_seller_id: str | None = ID
    terms: str | None = TEXT
    attachment_ids: list[str] | None = Field(default=None, max_length=20)


class InstallmentRequest(_Strict):
    id: str | None = ID
    amount: int
    mode_id: str = REF
    paid_on: date | None = None
    """Absent : aujourd'hui (Douala)."""
    reference: str | None = SHORT


class ReasonRequest(_Strict):
    reason: str | None = TEXT


class ReminderRequest(_Strict):
    id: str | None = ID
    remind_on: date
    note: str | None = TEXT


class ReminderPatch(_Strict):
    status: ReminderStatus | None = None
    remind_on: date | None = None
    note: str | None = TEXT


class GuarantorRequest(_Strict):
    id: str | None = ID
    name: str = Field(max_length=120)
    phone: str = Field(max_length=32)
    relation: str | None = Field(default=None, max_length=200)
    id_doc_type: IdDocumentType | None = None
    id_doc_number: str | None = Field(default=None, max_length=200)
    id_doc_photo_id: str | None = ID
