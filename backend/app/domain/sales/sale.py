"""Agrégat `Sale` : vente `V-000001` (UC-VEN-01, 02, 07, 08 ; CDC § 20.4).

- Numéro définitif attribué à la création (RG-T05), jamais changé ; numéro provisoire gardé
  s'il y en a un (RG-T06, saisie hors connexion, T23).
- Lieu de vente, vendeur, type (Comptant / Crédit) et articles / quantités : fixés à la
  création. Le contenu modifiable (`SaleContent`) suit les règles de `rules.py`.
- Totaux calculés : total, payé (paiements de la vente), reste à payer (total - payé). Les
  versements sur créance sont tenus par T17 : ils ne modifient pas la vente.
- Statut Valide / Annulée : une vente annulée reste visible, ne se modifie plus et sort de
  tous les totaux (RG-T03, H11).
"""

from dataclasses import dataclass, field
from datetime import datetime

from app.domain.audit.values import EntityRef, Performer
from app.domain.purchasing.rules import clean_reason
from app.domain.purchasing.values import Cancellation, Capture, changes_between
from app.domain.sales import events as ev
from app.domain.sales.ids import SaleId
from app.domain.sales.receivable_events import (
    CreditSaleAmountsChanged,
    CreditSaleCancelled,
    CreditSaleRecorded,
)
from app.domain.sales.rules import check_content, check_same_lines, paid_of, sale_total
from app.domain.sales.values import CreditTerms, SaleContent, SaleKind, SaleStatus, sale_instant
from app.domain.shared.doc_number import DocNumber, DocType, ProvisionalDocNumber
from app.domain.shared.errors import InvalidStateTransition
from app.domain.shared.events import EventCollector
from app.domain.shared.ids import ShopId, UserId
from app.domain.shared.money import Money
from app.domain.shops.ids import LocationId


@dataclass(eq=False, kw_only=True)
class Sale:
    id: SaleId
    shop_id: ShopId
    number: DocNumber
    kind: SaleKind
    location_id: LocationId
    seller_id: UserId
    content: SaleContent
    capture: Capture
    credit: CreditTerms | None = None
    provisional_number: ProvisionalDocNumber | None = None
    stock_to_verify: bool = False
    cancellation: Cancellation | None = None
    version: int = 0
    events: EventCollector = field(default_factory=EventCollector, repr=False)

    def __post_init__(self) -> None:
        if self.number.doc_type is not DocType.SALE:
            msg = f"Numéro de vente attendu (V-…), reçu {self.number}"
            raise ValueError(msg)
        self.kind = SaleKind(self.kind)
        if (self.kind is SaleKind.CREDIT) != (self.credit is not None):
            msg = "Les conditions de crédit vont avec une vente à crédit, et elle seule"
            raise ValueError(msg)

    # ------------------------------------------------------------------ lectures
    @property
    def status(self) -> SaleStatus:
        return SaleStatus.VALID if self.cancellation is None else SaleStatus.CANCELLED

    @property
    def entity(self) -> EntityRef:
        return EntityRef("sale", self.id.value, str(self.number))

    @property
    def sold_at(self) -> datetime:
        return sale_instant(self.content.sold_on, self.capture.received_at)

    @property
    def total(self) -> Money:
        return sale_total(self.content.lines)

    @property
    def paid(self) -> Money:
        return paid_of(self.content)

    @property
    def remaining(self) -> Money:
        return self.total - self.paid

    def require_valid(self) -> None:
        if self.cancellation is not None:
            msg = "Cette vente est annulée"
            raise InvalidStateTransition(msg, details={"status": self.status.value})

    # ------------------------------------------------------------------ cycle de vie
    def record(self, *, performer: Performer, below_minimum: bool) -> None:
        """Valide la vente neuve et dépose ses événements (journal, créance T17)."""
        if self.version != 0 or len(self.events):
            msg = "Sale.record attend une vente neuve"
            raise ValueError(msg)
        check_content(self.kind, self.content, creating=True)
        event = ev.SaleRecordedBelowMinimum if below_minimum else ev.SaleRecorded
        suffix = " (sous le prix minimum)" if below_minimum else ""
        self.events.record(
            event(
                shop_id=self.shop_id,
                occurred_at=self.capture.received_at,
                performer=performer,
                entity=self.entity,
                summary=f"Vente {self.number} enregistrée : {self.total}{suffix}",
                captured_at=self.capture.captured_at,
            )
        )
        customer = self.content.customer_id
        if self.credit is not None and customer is not None:
            self.events.record(
                CreditSaleRecorded(
                    shop_id=self.shop_id,
                    occurred_at=self.capture.received_at,
                    sale_id=self.id,
                    sale_number=str(self.number),
                    customer_id=customer,
                    responsible_seller_id=self.seller_id,
                    initial_amount=self.remaining,
                    opened_on=self.content.sold_on,
                    reminder_on=self.credit.reminder_on,
                    terms=self.credit.terms,
                )
            )

    def modify(
        self, content: SaleContent, *, reason: str, performer: Performer, now: datetime
    ) -> bool:
        """UC-VEN-07 : nouveau contenu, motif obligatoire ; `False` si rien ne change."""
        self.require_valid()
        cleaned = clean_reason(reason)
        check_same_lines(self.content.lines, content.lines)
        check_content(self.kind, content, creating=False)
        changes = changes_between(self.content.scalars(), content.scalars())
        if not changes:
            return False
        before = (self.total, self.paid, self.content.customer_id)
        self.content = content
        repriced = any(change.field.endswith("_unit_price") for change in changes)
        event = ev.SalePriceModified if repriced else ev.SaleModified
        self.events.record(
            event(
                shop_id=self.shop_id,
                occurred_at=now,
                performer=performer,
                entity=self.entity,
                summary=f"Vente {self.number} modifiée",
                changes=changes,
                reason=cleaned,
            )
        )
        customer = content.customer_id
        changed = before != (self.total, self.paid, customer)
        if self.credit is not None and customer is not None and changed:
            self.events.record(
                CreditSaleAmountsChanged(
                    shop_id=self.shop_id,
                    occurred_at=now,
                    sale_id=self.id,
                    customer_id=customer,
                    total=self.total,
                    paid_at_sale=self.paid,
                    initial_amount=self.remaining,
                )
            )
        return True

    def cancel(
        self, reason: str, *, refund_payments: bool, performer: Performer, now: datetime
    ) -> None:
        """UC-VEN-08 : annule avec motif ; ne se défait pas (une seconde fois → 422)."""
        self.require_valid()
        cleaned = clean_reason(reason)
        self.cancellation = Cancellation(now, performer.user_id, cleaned)
        self.events.record(
            ev.SaleCancelled(
                shop_id=self.shop_id,
                occurred_at=now,
                performer=performer,
                entity=self.entity,
                summary=f"Vente {self.number} annulée",
                reason=cleaned,
            )
        )
        if self.credit is not None:
            self.events.record(
                CreditSaleCancelled(
                    shop_id=self.shop_id,
                    occurred_at=now,
                    sale_id=self.id,
                    refund_payments=refund_payments,
                )
            )
