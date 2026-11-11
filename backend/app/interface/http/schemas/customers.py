"""Schémas des clients (UC-VEN-11) : création idempotente par `id`, `PATCH` + `version`.
Téléphone saisi librement (« 690 00 00 00 »), rendu en E.164 (« +237690000000 »)."""

from pydantic import BaseModel, ConfigDict, Field

from app.domain.sales.customer import CustomerKind, IdDocumentType
from app.interface.http.schemas.sales import SaleResponse

ID = Field(default=None, max_length=64)
OPTIONAL = Field(default=None, max_length=200)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CustomerCreateRequest(_Strict):
    id: str | None = ID
    name: str = Field(max_length=120)
    phone: str = Field(max_length=32)
    kind: CustomerKind = CustomerKind.INDIVIDUAL
    city: str | None = OPTIONAL
    address: str | None = OPTIONAL
    id_doc_type: IdDocumentType | None = None
    id_doc_number: str | None = OPTIONAL
    id_doc_photo_id: str | None = ID
    credit_limit: int | None = None
    note: str | None = Field(default=None, max_length=500)


class CustomerPatch(_Strict):
    version: int
    name: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=32)
    kind: CustomerKind | None = None
    city: str | None = OPTIONAL
    address: str | None = OPTIONAL
    id_doc_type: IdDocumentType | None = None
    id_doc_number: str | None = OPTIONAL
    id_doc_photo_id: str | None = ID
    credit_limit: int | None = None
    note: str | None = Field(default=None, max_length=500)


class CustomerResponse(BaseModel):
    id: str
    name: str
    phone: str
    kind: str
    city: str | None
    address: str | None
    id_doc_type: str | None
    id_doc_number: str | None
    id_doc_photo_id: str | None
    credit_limit: int | None
    note: str | None
    created_by: str
    version: int


class CustomerListResponse(BaseModel):
    items: list[CustomerResponse]


class CustomerSheetResponse(BaseModel):
    customer: CustomerResponse
    total_bought: int
    total_due: int
    sales: list[SaleResponse]
