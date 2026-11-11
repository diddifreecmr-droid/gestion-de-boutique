"""Saisies d'une vente (specs § 6.4), avant vérification par `SaleResolver`.

Forme de `POST /sales` : lieu, date (`sold_on`), type, client (existant par `id` ou créé à la
volée par nom + téléphone + type, UC-VEN-02), lignes (article, mode, quantité, prix vendu,
détails par unité), paiements, conditions de crédit, demande de prix (T16b), note.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.domain.catalog.ids import ArticleId
from app.domain.sales.customer import CustomerKind
from app.domain.sales.ids import CustomerId, PriceRequestId, SalePaymentId
from app.domain.sales.lines import SaleMode, SoldDetail
from app.domain.sales.values import CreditTerms, SaleKind
from app.domain.shared.ids import UserId
from app.domain.shops.ids import LocationId, PaymentModeId


@dataclass(frozen=True, slots=True, kw_only=True)
class LineInput:
    article_id: ArticleId
    quantity: Decimal | int | str
    unit_price: int
    sale_mode: SaleMode | None = None
    """Absent : « à l'unité », ou « au mètre » pour un article stocké en mètres."""
    details: tuple[SoldDetail, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class PaymentInput:
    mode_id: PaymentModeId
    amount: int
    reference: str | None = None
    payment_id: SalePaymentId | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class CustomerInput:
    """`customer_id` : client existant ; sinon création rapide (fusion par téléphone)."""

    customer_id: CustomerId | None = None
    name: str | None = None
    phone: str | None = None
    kind: CustomerKind = CustomerKind.INDIVIDUAL


@dataclass(frozen=True, slots=True, kw_only=True)
class SaleInput:
    kind: SaleKind
    lines: tuple[LineInput, ...]
    payments: tuple[PaymentInput, ...] = ()
    sold_on: date | None = None
    location_id: LocationId | None = None
    customer: CustomerInput | None = None
    credit: CreditTerms | None = None
    note: str | None = None
    seller_id: UserId | None = None
    """Vendeur attribué : le propriétaire peut en choisir un (CDC § 20.4) ; sinon l'auteur."""
    price_request_id: PriceRequestId | None = None
    """Accord du propriétaire pour un prix sous le minimum (UC-VEN-03, `price_approval.py`)."""
