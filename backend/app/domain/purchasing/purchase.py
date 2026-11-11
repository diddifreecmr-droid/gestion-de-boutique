"""Agrégat `Purchase` : achat `A-000001` (UC-ACH-01, 03, 04, 06 ; CDC § 20.3).

- Numéro définitif attribué à la création (RG-T05) ; il ne change jamais, même corrigé.
- Contenu saisi (`PurchaseDetails`) et son chiffrage (`CostedLine`, calculé par
  `cost_lines`) ; totaux calculés : marchandise, frais, total (RG-T10).
- Statut Valide / Annulé ; un achat annulé reste visible, ne se corrige plus, ne reçoit plus
  de paiement et sort de tous les totaux (RG-T03).
- Délai de correction (UC-ACH-03, PUR-07) : le comptable corrige **jusqu'à J+7 inclus** après
  la date d'achat (achat du 03/11 : le 10/11 oui, le 11/11 non) ; le propriétaire toujours.
- Les mouvements de stock et les coûts des articles sont posés par l'application (grand
  livre, rejeu du CMP) dans la même transaction ; les ventes passées gardent leurs coûts
  figés (RG-T13) : une correction ne les touche jamais.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from app.domain.audit.values import EntityRef, Performer
from app.domain.purchasing.errors import CorrectionWindowClosed, Overpayment
from app.domain.purchasing.events import (
    PurchaseCancelled,
    PurchaseCorrected,
    PurchaseRecorded,
)
from app.domain.purchasing.ids import PurchaseId
from app.domain.purchasing.lines import CostedLine
from app.domain.purchasing.payments import PaymentStatus, SupplierPayment, payment_status
from app.domain.purchasing.rules import (
    CORRECTION_DAYS,
    PurchaseStatus,
    check_costing,
    clean_reason,
    purchase_total,
)
from app.domain.purchasing.values import (
    Cancellation,
    Capture,
    PurchaseDetails,
    changes_between,
    entry_instant,
)
from app.domain.shared.doc_number import DocNumber, DocType
from app.domain.shared.errors import InvalidStateTransition
from app.domain.shared.events import EventCollector
from app.domain.shared.ids import ShopId
from app.domain.shared.money import Money


@dataclass(eq=False, kw_only=True)
class Purchase:
    id: PurchaseId
    shop_id: ShopId
    number: DocNumber
    details: PurchaseDetails
    costed: tuple[CostedLine, ...]
    capture: Capture
    payments: tuple[SupplierPayment, ...] = ()
    cancellation: Cancellation | None = None
    version: int = 0
    events: EventCollector = field(default_factory=EventCollector, repr=False)

    def __post_init__(self) -> None:
        if self.number.doc_type is not DocType.PURCHASE:
            msg = f"Numéro d'achat attendu (A-…), reçu {self.number}"
            raise ValueError(msg)
        self.costed = tuple(self.costed)
        self.payments = tuple(self.payments)
        check_costing(self.details, self.costed)

    # ------------------------------------------------------------------ lectures
    @property
    def status(self) -> PurchaseStatus:
        return PurchaseStatus.VALID if self.cancellation is None else PurchaseStatus.CANCELLED

    @property
    def entity(self) -> EntityRef:
        return EntityRef("purchase", self.id.value, str(self.number))

    @property
    def merchandise_total(self) -> Money:
        return Money.total(line.total for line in self.costed)

    @property
    def fees_total(self) -> Money:
        return Money.total(fee.amount for fee in self.details.fees)

    @property
    def total(self) -> Money:
        return purchase_total(self.costed, self.details.fees)

    @property
    def paid(self) -> Money:
        return Money.total(payment.amount for payment in self.payments)

    @property
    def payment_status(self) -> PaymentStatus:
        return payment_status(self.total, self.paid)

    @property
    def entry_instant(self) -> datetime:
        return entry_instant(self.details.purchase_date, self.capture.received_at)

    @property
    def last_correction_day(self) -> date:
        return self.details.purchase_date + timedelta(days=CORRECTION_DAYS)

    # ------------------------------------------------------------------ cycle de vie
    @classmethod
    def record(
        cls,
        shop_id: ShopId,
        number: DocNumber,
        details: PurchaseDetails,
        costed: tuple[CostedLine, ...],
        capture: Capture,
        *,
        performer: Performer,
        purchase_id: PurchaseId | None = None,
    ) -> "Purchase":
        purchase = cls(
            id=purchase_id or PurchaseId.new(),
            shop_id=shop_id,
            number=number,
            details=details,
            costed=costed,
            capture=capture,
        )
        purchase.events.record(
            PurchaseRecorded(
                shop_id=shop_id,
                occurred_at=capture.received_at,
                performer=performer,
                entity=purchase.entity,
                summary=f"Achat {number} enregistré : {purchase.total}",
                captured_at=capture.captured_at,
            )
        )
        return purchase

    def require_valid(self) -> None:
        if self.cancellation is not None:
            msg = "Cet achat est annulé"
            raise InvalidStateTransition(msg, details={"status": self.status.value})

    def require_correctable(self, *, by_owner: bool, today: date) -> None:
        """Valide, et dans le délai du comptable sauf pour le propriétaire (UC-ACH-03)."""
        self.require_valid()
        if not by_owner and today > self.last_correction_day:
            raise CorrectionWindowClosed(self.last_correction_day)

    def correct(
        self,
        details: PurchaseDetails,
        costed: tuple[CostedLine, ...],
        *,
        reason: str,
        performer: Performer,
        now: datetime,
    ) -> bool:
        """Nouveau contenu (motif obligatoire) ; `False` si rien ne change (UC-ACH-03)."""
        self.require_valid()
        cleaned = clean_reason(reason)
        check_costing(details, costed)
        changes = changes_between(self.details.scalars(), details.scalars())
        if not changes:
            return False
        total = purchase_total(costed, details.fees)
        if self.paid > total:
            raise Overpayment(total=total, paid=self.paid)
        self.details, self.costed = details, costed
        self.events.record(
            PurchaseCorrected(
                shop_id=self.shop_id,
                occurred_at=now,
                performer=performer,
                entity=self.entity,
                summary=f"Achat {self.number} corrigé",
                changes=changes,
                reason=cleaned,
            )
        )
        return True

    def cancel(self, reason: str, *, performer: Performer, now: datetime) -> None:
        """Annule avec motif (UC-ACH-04) ; ne se défait pas."""
        self.require_valid()
        cleaned = clean_reason(reason)
        self.cancellation = Cancellation(now, performer.user_id, cleaned)
        self.events.record(
            PurchaseCancelled(
                shop_id=self.shop_id,
                occurred_at=now,
                performer=performer,
                entity=self.entity,
                summary=f"Achat {self.number} annulé",
                reason=cleaned,
            )
        )
