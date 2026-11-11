"""Corps de requête du module Ventes (specs § 6.4, § 6.1) : `id` client idempotent (rejeu →
200), montants entiers FCFA, quantités en chaînes décimales (`"1"`, `"2.5"`), `PATCH` +
`version` + `reason`. Champs inconnus refusés (400)."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.domain.sales.customer import CustomerKind
from app.domain.sales.lines import SaleMode
from app.domain.sales.values import SaleKind

ID = Field(default=None, max_length=64)
REF = Field(max_length=64)
TEXT = Field(default=None, max_length=500)
SHORT = Field(default=None, max_length=64)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DetailRequest(_Strict):
    """Détail d'une unité vendue (CDC § 17.3) : tous facultatifs."""

    color: str | None = SHORT
    chassis_number: str | None = SHORT
    engine_number: str | None = SHORT
    size: str | None = SHORT


class SaleLineRequest(_Strict):
    article_id: str = REF
    sale_mode: SaleMode | None = None
    """Absent : « unit », ou « meter » pour un article stocké en mètres."""
    quantity: str = Field(max_length=16)
    unit_price: int
    details: list[DetailRequest] = Field(default_factory=list, max_length=100)


class SalePaymentRequest(_Strict):
    id: str | None = ID
    mode_id: str = REF
    amount: int
    reference: str | None = SHORT


class SaleCustomerRequest(_Strict):
    """Client existant (`id`) ou créé à la volée (`id: null` + nom + téléphone + type)."""

    id: str | None = ID
    name: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=32)
    kind: CustomerKind = CustomerKind.INDIVIDUAL


class CreditRequest(_Strict):
    reminder_on: date | None = None
    terms: str | None = TEXT
    guarantor: None = None
    """Garant : saisi sur la créance (T17) ; seul `null` est accepté ici."""


class SaleCreateRequest(_Strict):
    id: str | None = ID
    location_id: str | None = ID
    """Absent : lieu habituel du vendeur ; le propriétaire choisit un point de vente."""
    sold_on: date | None = None
    kind: SaleKind
    customer: SaleCustomerRequest | None = None
    lines: list[SaleLineRequest] = Field(min_length=1, max_length=50)
    payments: list[SalePaymentRequest] = Field(default_factory=list, max_length=10)
    credit: CreditRequest | None = None
    price_request_id: str | None = ID
    """Accord de prix sous le minimum (UC-VEN-03) : demande acceptée qui couvre la ligne."""
    seller_id: str | None = ID
    note: str | None = TEXT


class LinePatchRequest(_Strict):
    """Ligne modifiée, dans l'ordre des lignes : prix et détails ; article / quantité
    facultatifs, comparés à ceux de la ligne (différents → `LINE_CHANGE_NOT_ALLOWED`)."""

    article_id: str | None = ID
    quantity: str | None = Field(default=None, max_length=16)
    unit_price: int | None = None
    details: list[DetailRequest] | None = Field(default=None, max_length=100)


class SalePatch(_Strict):
    version: int
    reason: str = Field(max_length=500)
    lines: list[LinePatchRequest] | None = Field(default=None, max_length=50)
    payments: list[SalePaymentRequest] | None = Field(default=None, max_length=10)
    customer: SaleCustomerRequest | None = None
    sold_on: date | None = None
    note: str | None = TEXT


class CancelSaleRequest(_Strict):
    reason: str = Field(max_length=500)
    refund_payments: bool = False
    """Vente à crédit : les versements déjà notés deviennent « à rembourser » (T17)."""


class ErrorReportRequest(_Strict):
    id: str | None = ID
    description: str = Field(max_length=500)


class ErrorReplyRequest(_Strict):
    reply: str = Field(max_length=500)
    handled: bool = True
    version: int | None = None
