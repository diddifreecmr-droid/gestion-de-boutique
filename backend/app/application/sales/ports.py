"""Ports du module Ventes (T16a), liés à la boutique (gabarit `ShopRecordRepository`).

- `CustomerRepository` : téléphone E.164 unique (`customer_phone`) ; `search` applique la
  portée « ses clients » **dans la requête** (`seller` : clients qu'il a créés ou qui ont une
  vente de lui, UC-VEN-11, Q-20).
- `SaleRepository` : numéro unique (`sale_number`) ; lectures par période (date de vente,
  annulées comprises : RG-T03, exclues des totaux par le cas d'utilisation), par référence
  (numéro, numéro provisoire, châssis, RG-M02), par client, et quantités vendues (classement
  « plus vendus »). `seller` restreint toujours **la requête** aux ventes de ce vendeur.
- `ChassisClaimRepository` : réservation des châssis vendus (`sold_chassis_active`, RG-M01).
- `ErrorReportRepository`, `ReceiptPrintRepository` (`receipt_print_sequence`).

Les noms des `UniqueKey` sont ceux des contraintes SQL (`tables_sales.py`).
"""

from abc import abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.application.ports.aggregate import UniqueKey
from app.application.ports.pagination import Cursor
from app.application.shops.ports import ShopRecordRepository
from app.domain.catalog.ids import ArticleId
from app.domain.catalog.keys import fold
from app.domain.identity.phone import PhoneNumber
from app.domain.sales.chassis import ChassisClaim
from app.domain.sales.customer import Customer
from app.domain.sales.error_report import ErrorReport
from app.domain.sales.ids import ChassisClaimId, CustomerId, ErrorReportId, ReceiptPrintId, SaleId
from app.domain.sales.receipt_print import ReceiptPrint
from app.domain.sales.sale import Sale
from app.domain.shared.ids import UserId

CUSTOMER_PHONE = "customer_phone"
SALE_NUMBER = "sale_number"
SOLD_CHASSIS_ACTIVE = "sold_chassis_active"
RECEIPT_PRINT_SEQUENCE = "receipt_print_sequence"


@dataclass(frozen=True, slots=True)
class CustomerQuery:
    """`text` : sous-chaîne pliée du nom ou chiffres du téléphone ; `seller` : portée OWN."""

    text: str | None = None
    seller: UserId | None = None

    @property
    def folded(self) -> str | None:
        """Terme plié ; un numéro (« 690 00 ») est compacté en chiffres (« 69000 »)."""
        folded = "" if self.text is None else fold(self.text)
        compact = folded.replace(" ", "")
        return (compact if compact.isdigit() else folded) or None

    def matches(self, customer: Customer) -> bool:
        """Filtre de texte de référence (adaptateur mémoire ; la portée est à part)."""
        text = self.folded
        return text is None or text in customer.search_key


class CustomerRepository(ShopRecordRepository[CustomerId, Customer]):
    def unique_keys(self) -> Sequence[UniqueKey[Customer]]:
        return (UniqueKey(CUSTOMER_PHONE, lambda customer: customer.phone_key),)

    @abstractmethod
    def find_by_phone(self, phone: PhoneNumber) -> Customer | None: ...

    @abstractmethod
    def search(self, query: CustomerQuery) -> list[Customer]:
        """Clients filtrés, par nom plié puis identifiant (`search_key` de `customer_search`)."""

    @abstractmethod
    def visible_to(self, customer_id: CustomerId, seller: UserId) -> bool:
        """Client créé par ce vendeur ou ayant au moins une vente de lui."""


class SaleRepository(ShopRecordRepository[SaleId, Sale]):
    def unique_keys(self) -> Sequence[UniqueKey[Sale]]:
        return (UniqueKey(SALE_NUMBER, lambda sale: str(sale.number)),)

    @abstractmethod
    def list_between(
        self, first_day: date, last_day: date, *, seller: UserId | None = None
    ) -> list[Sale]:
        """Ventes datées de `[first_day, last_day]`, plus récentes d'abord (`position`)."""

    @abstractmethod
    def cancelled_between(
        self, first_day: date, last_day: date, *, seller: UserId | None = None
    ) -> list[Sale]:
        """Ventes annulées pendant `[first_day, last_day]` (journées de Douala, Q-09)."""

    @abstractmethod
    def find_by_reference(
        self, number: str | None, chassis: str | None, *, seller: UserId | None = None
    ) -> list[Sale]:
        """Ventes de numéro (définitif ou provisoire) `number` **ou** portant le châssis de clé
        `chassis` (toutes dates), plus récentes d'abord."""

    @abstractmethod
    def for_customer(self, customer_id: CustomerId, *, seller: UserId | None = None) -> list[Sale]:
        """Ventes du client (annulées comprises), plus récentes d'abord."""

    @abstractmethod
    def quantities_since(self, since: datetime) -> dict[ArticleId, Decimal]:
        """Quantités de stock vendues par article depuis `since`, ventes annulées exclues."""


def position(sale: Sale) -> Cursor:
    """Ordre des listes (UC-VEN-05) : instant de vente décroissant, puis `id`."""
    return Cursor(sale.sold_at, sale.id.value)


class ChassisClaimRepository(ShopRecordRepository[ChassisClaimId, ChassisClaim]):
    def unique_keys(self) -> Sequence[UniqueKey[ChassisClaim]]:
        return (UniqueKey(SOLD_CHASSIS_ACTIVE, lambda claim: claim.active_key),)

    @abstractmethod
    def find_active(self, key: str) -> ChassisClaim | None:
        """Réservation **active** du châssis de clé `key`, s'il y en a une."""

    @abstractmethod
    def for_sale(self, sale_id: SaleId) -> list[ChassisClaim]:
        """Réservations de la vente (actives ou libérées)."""


class ErrorReportRepository(ShopRecordRepository[ErrorReportId, ErrorReport]):
    @abstractmethod
    def for_sale(self, sale_id: SaleId) -> list[ErrorReport]:
        """Signalements de la vente, du plus ancien au plus récent."""


class ReceiptPrintRepository(ShopRecordRepository[ReceiptPrintId, ReceiptPrint]):
    def unique_keys(self) -> Sequence[UniqueKey[ReceiptPrint]]:
        return (UniqueKey(RECEIPT_PRINT_SEQUENCE, lambda printed: printed.sequence_key),)

    @abstractmethod
    def count_for(self, sale_id: SaleId) -> int:
        """Nombre d'impressions déjà inscrites pour la vente."""
