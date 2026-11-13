"""État calculé d'une créance (CDC § 10.1, § 20.5), partagé par l'agrégat et ses opérations.

Montant initial, total versé et reste sont **calculés** à partir des versements valides
(specs § 5.4) : reste = initial - versé. Après une mise en perte, le reste reste affiché et
plafonne les récupérations (**Q-22** : SCN-08 → 150 000 après 100 000 récupérés) ; une
récupération totale laisse la créance En perte (§ 7.1 « EnPerte → EnPerte »).
"""

from datetime import date, datetime

from app.domain.audit.values import EntityRef
from app.domain.catalog.ids import AttachmentId
from app.domain.receivables.follow_up import Guarantor, Reminder
from app.domain.receivables.ids import InstallmentId, ReceivableId, ReminderId
from app.domain.receivables.installment import Installment, total_of
from app.domain.receivables.values import (
    ReceivableOrigin,
    ReceivableStatus,
    SaleCancellation,
    WriteOff,
)
from app.domain.sales.ids import CustomerId, SaleId
from app.domain.shared.errors import InvalidStateTransition, NotFound
from app.domain.shared.events import EventCollector
from app.domain.shared.ids import ShopId, UserId
from app.domain.shared.money import Money


def not_found(entity_id: object) -> NotFound:
    """Même erreur que les dépôts (« Élément introuvable ») : aucune fuite d'existence."""
    return NotFound("Élément introuvable", details={"id": str(entity_id)})


class ReceivableState:
    """Attributs (posés par la dataclass `Receivable`) et lectures calculées."""

    id: ReceivableId
    shop_id: ShopId
    customer_id: CustomerId
    origin: ReceivableOrigin
    opened_on: date
    initial_amount: Money
    recorded_at: datetime
    sale_id: SaleId | None
    sale_number: str | None
    sale_total: Money | None
    paid_at_sale: Money
    description: str | None
    responsible_seller_id: UserId | None
    terms: str | None
    installments: tuple[Installment, ...]
    reminders: tuple[Reminder, ...]
    guarantors: tuple[Guarantor, ...]
    attachment_ids: tuple[AttachmentId, ...]
    write_off: WriteOff | None
    sale_cancellation: SaleCancellation | None
    version: int
    events: EventCollector

    @property
    def total_paid(self) -> Money:
        return total_of(self.installments)

    @property
    def remaining(self) -> Money:
        return self.initial_amount - self.total_paid

    @property
    def status(self) -> ReceivableStatus:
        if self.sale_cancellation is not None:
            return ReceivableStatus.CANCELLED
        if self.write_off is not None:
            return ReceivableStatus.WRITTEN_OFF
        if self.remaining.amount == 0:
            return ReceivableStatus.SETTLED
        return ReceivableStatus.OPEN

    @property
    def counts_as_due(self) -> bool:
        """Compte dans le « total à recevoir » et le dû du client (§ 10.1 : En cours seule)."""
        return self.status is ReceivableStatus.OPEN

    @property
    def entity(self) -> EntityRef:
        label = self.sale_number or (self.description or "Créance ancienne")[:500]
        return EntityRef("receivable", self.id.value, label)

    @property
    def last_installment_on(self) -> date | None:
        days = [i.paid_on for i in self.installments if i.valid]
        return max(days) if days else None

    def seniority(self, today: date) -> int:
        """Ancienneté en jours depuis la date d'ouverture (jamais négative)."""
        return max((today - self.opened_on).days, 0)

    def installment(self, installment_id: InstallmentId) -> Installment:
        for item in self.installments:
            if item.id == installment_id:
                return item
        raise not_found(installment_id)

    def reminder(self, reminder_id: ReminderId) -> Reminder:
        for item in self.reminders:
            if item.id == reminder_id:
                return item
        raise not_found(reminder_id)

    def require_not_cancelled(self) -> None:
        if self.sale_cancellation is not None:
            msg = "Cette créance est annulée (vente ou import annulé)"
            raise InvalidStateTransition(msg, details={"status": self.status.value})
