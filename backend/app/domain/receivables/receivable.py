"""Agrégat `Receivable` : créance d'un client (UC-CRE-01, UC-CRE-02 ; CDC § 10, § 20.5).

- Origine **Vente** (`open_from_sale`, depuis `CreditSaleRecorded`, même transaction que la
  vente) : vente liée, total et acompte de la vente, montant initial = total - acompte,
  vendeur responsable = vendeur de la vente, conditions et rappel convenus.
- Origine **Ancienne** (`open_legacy`, propriétaire) : montant dû aujourd'hui, date
  d'origine, description obligatoire, vendeur responsable facultatif ; elle ne compte ni dans
  les ventes ni dans les marges (aucune vente, aucun mouvement de stock).
- Statut, total versé, reste, ancienneté : calculés (`state.py`) ; opérations dans
  `book.py` (versements, perte), `sale_link.py` (vente liée) et `tracking.py` (suivi).
"""

from dataclasses import dataclass, field
from datetime import date, datetime

from app.domain.audit.values import Performer
from app.domain.catalog.ids import AttachmentId
from app.domain.receivables import events as ev
from app.domain.receivables.book import InstallmentBook
from app.domain.receivables.follow_up import Guarantor, Reminder
from app.domain.receivables.ids import ReceivableId, ReminderId, receivable_id_for_sale
from app.domain.receivables.installment import Installment
from app.domain.receivables.sale_link import SaleLink
from app.domain.receivables.tracking import Tracking
from app.domain.receivables.values import (
    DESCRIPTION_MAX_LENGTH,
    ReceivableOrigin,
    SaleCancellation,
    WriteOff,
    require_day,
)
from app.domain.sales.ids import CustomerId, SaleId
from app.domain.sales.receivable_events import CreditSaleRecorded
from app.domain.shared.business_day import require_aware
from app.domain.shared.errors import InvalidAmount
from app.domain.shared.events import EventCollector
from app.domain.shared.ids import ShopId, UserId
from app.domain.shared.money import Money
from app.domain.shops.values import clean_optional, clean_text


@dataclass(eq=False, kw_only=True)
class Receivable(InstallmentBook, SaleLink, Tracking):
    id: ReceivableId
    shop_id: ShopId
    customer_id: CustomerId
    origin: ReceivableOrigin
    opened_on: date
    initial_amount: Money
    recorded_at: datetime
    sale_id: SaleId | None = None
    sale_number: str | None = None
    sale_total: Money | None = None
    paid_at_sale: Money = field(default_factory=Money.zero)
    description: str | None = None
    responsible_seller_id: UserId | None = None
    terms: str | None = None
    installments: tuple[Installment, ...] = ()
    reminders: tuple[Reminder, ...] = ()
    guarantors: tuple[Guarantor, ...] = ()
    attachment_ids: tuple[AttachmentId, ...] = ()
    write_off: WriteOff | None = None
    sale_cancellation: SaleCancellation | None = None
    version: int = 0
    events: EventCollector = field(default_factory=EventCollector, repr=False)

    def __post_init__(self) -> None:
        self.origin = ReceivableOrigin(self.origin)
        require_day(self.opened_on, "Receivable.opened_on")
        self.recorded_at = require_aware(self.recorded_at)
        self.initial_amount.require_non_negative("initial_amount")
        from_sale = self.origin is ReceivableOrigin.SALE
        if from_sale != (self.sale_id is not None):
            msg = "Une créance d'origine Vente a une vente liée, et elle seule"
            raise ValueError(msg)
        sale = self.sale_id
        if sale is not None and self.id != receivable_id_for_sale(sale):
            msg = "La créance d'une vente porte l'identifiant de cette vente"
            raise ValueError(msg)
        self.description = clean_optional(
            self.description, "description", max_length=DESCRIPTION_MAX_LENGTH
        )
        if not from_sale and self.description is None:
            clean_text(self.description, "description", max_length=DESCRIPTION_MAX_LENGTH)

    @classmethod
    def open_from_sale(cls, event: CreditSaleRecorded, *, total: Money) -> "Receivable":
        """UC-CRE-01 : `total` = total de la vente (l'acompte = total - montant initial)."""
        receivable = cls(
            id=receivable_id_for_sale(event.sale_id),
            shop_id=event.shop_id,
            customer_id=event.customer_id,
            origin=ReceivableOrigin.SALE,
            opened_on=event.opened_on,
            initial_amount=event.initial_amount,
            recorded_at=event.occurred_at,
            sale_id=event.sale_id,
            sale_number=event.sale_number,
            sale_total=total,
            paid_at_sale=total - event.initial_amount,
            responsible_seller_id=event.responsible_seller_id,
            terms=event.terms,
        )
        if event.reminder_on is not None:
            reminder = Reminder(
                id=ReminderId.new(),
                remind_on=event.reminder_on,
                created_by=event.responsible_seller_id,
                created_at=event.occurred_at,
            )
            receivable.reminders = (reminder,)
        receivable.events.record(
            ev.ReceivableOpened(
                shop_id=event.shop_id, occurred_at=event.occurred_at, receivable_id=receivable.id
            )
        )
        return receivable

    @classmethod
    def open_legacy(
        cls,
        shop_id: ShopId,
        *,
        receivable_id: ReceivableId,
        customer_id: CustomerId,
        amount: Money,
        opened_on: date,
        description: str,
        responsible_seller_id: UserId | None,
        terms: str | None,
        performer: Performer,
        now: datetime,
    ) -> "Receivable":
        """UC-CRE-02 : créance ancienne (propriétaire), montant > 0."""
        if amount.amount <= 0:
            msg = "Le montant d'une créance ancienne doit être supérieur à 0"
            raise InvalidAmount(msg, details={"field": "amount"})
        receivable = cls(
            id=receivable_id,
            shop_id=shop_id,
            customer_id=customer_id,
            origin=ReceivableOrigin.LEGACY,
            opened_on=opened_on,
            initial_amount=amount,
            recorded_at=now,
            description=clean_text(description, "description", max_length=DESCRIPTION_MAX_LENGTH),
            responsible_seller_id=responsible_seller_id,
            terms=clean_optional(terms, "terms"),
        )
        receivable.events.record(
            ev.LegacyReceivableRecorded(
                shop_id=shop_id,
                occurred_at=now,
                performer=performer,
                entity=receivable.entity,
                summary=f"Créance ancienne enregistrée : {amount}",
            )
        )
        return receivable
