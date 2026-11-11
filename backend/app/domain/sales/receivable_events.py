"""Événements de la vente destinés au module Créances (T17), **non journalisés** (`NotAudited`).

La vente elle-même est journalisée (`SaleRecorded`, `SaleModified`, `SaleCancelled`) ; ces
événements ne portent que ce dont T17 a besoin pour tenir la créance, dans la même transaction
(un handler branché sur l'unité de travail) :

- `CreditSaleRecorded` (UC-CRE-01) : ouvrir la créance — client, vente liée, montant initial
  (= reste à payer : total - acompte), date d'ouverture (jour de la vente), vendeur
  responsable (celui de la vente), date de rappel et conditions convenues ;
- `CreditSaleAmountsChanged` (UC-VEN-07, MOD-01) : total ou acompte modifié → recalculer le
  montant initial (780 000 → 760 000 : créance 480 000 → 460 000) ; client changé ;
- `CreditSaleCancelled` (UC-VEN-08, SCN-06) : la créance passe « Annulée » (hors total à
  recevoir) ; `refund_payments` vrai → ses versements deviennent « à rembourser ».

Tant que T17 n'est pas livré, aucun handler ne les consomme : ils sont simplement remis.
"""

from dataclasses import dataclass
from datetime import date

from app.domain.audit.events import NotAudited
from app.domain.sales.ids import CustomerId, SaleId
from app.domain.shared.events import DomainEvent
from app.domain.shared.ids import UserId
from app.domain.shared.money import Money


@dataclass(frozen=True, kw_only=True)
class CreditSaleRecorded(DomainEvent, NotAudited):
    sale_id: SaleId
    sale_number: str
    customer_id: CustomerId
    responsible_seller_id: UserId
    initial_amount: Money
    opened_on: date
    reminder_on: date | None = None
    terms: str | None = None


@dataclass(frozen=True, kw_only=True)
class CreditSaleAmountsChanged(DomainEvent, NotAudited):
    sale_id: SaleId
    customer_id: CustomerId
    total: Money
    paid_at_sale: Money
    initial_amount: Money


@dataclass(frozen=True, kw_only=True)
class CreditSaleCancelled(DomainEvent, NotAudited):
    sale_id: SaleId
    refund_payments: bool
