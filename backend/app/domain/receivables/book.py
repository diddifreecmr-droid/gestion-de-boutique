"""Versements et mise en perte d'une créance (UC-CRE-03, UC-CRE-08, UC-CRE-09 ; § 7.1).

- `record_installment` : créance non annulée, montant ≤ reste (`OVERPAYMENT`, une créance
  Soldée n'accepte donc plus rien : SCN-07 étape 4). Reste à 0 → Soldée (calculé). Créance
  En perte → nature « Récupération sur perte », statut inchangé.
- `cancel_installment` : motif obligatoire, versement valide ; le reste est recalculé et une
  créance Soldée redevient En cours (SCN-07 étape 7).
- `write_off` : En cours seulement (Soldée, Annulée ou déjà En perte → 422) ; motif et date.
"""

from datetime import date, datetime

from app.domain.audit.values import Performer
from app.domain.purchasing.rules import clean_reason
from app.domain.purchasing.values import Cancellation
from app.domain.receivables import events as ev
from app.domain.receivables.errors import ReceivableOverpayment
from app.domain.receivables.ids import InstallmentId
from app.domain.receivables.installment import Installment, InstallmentNature
from app.domain.receivables.state import ReceivableState
from app.domain.receivables.values import ReceivableStatus, WriteOff
from app.domain.shared.errors import InvalidStateTransition


class InstallmentBook(ReceivableState):
    def record_installment(self, installment: Installment, *, performer: Performer) -> None:
        self.require_not_cancelled()
        if installment.amount > self.remaining:
            raise ReceivableOverpayment(remaining=self.remaining, amount=installment.amount)
        if any(item.number == installment.number for item in self.installments):
            msg = f"Numéro de versement déjà utilisé : {installment.number}"
            raise ValueError(msg)
        recovery = self.status is ReceivableStatus.WRITTEN_OFF
        nature = InstallmentNature.RECOVERY if recovery else InstallmentNature.NORMAL
        if installment.nature is not nature:
            msg = "La nature d'un versement est calculée par la créance"
            raise ValueError(msg)
        self.installments = (*self.installments, installment)
        settled = " — soldée" if self.status is ReceivableStatus.SETTLED else ""
        label = " (récupération sur perte)" if recovery else ""
        self.events.record(
            ev.InstallmentRecorded(
                shop_id=self.shop_id,
                occurred_at=installment.capture.received_at,
                performer=performer,
                entity=installment.entity,
                summary=f"Versement {installment.number} : {installment.amount}{label}{settled}",
            )
        )

    def nature_for_next(self) -> InstallmentNature:
        """Nature d'un versement enregistré maintenant (UC-CRE-09)."""
        if self.status is ReceivableStatus.WRITTEN_OFF:
            return InstallmentNature.RECOVERY
        return InstallmentNature.NORMAL

    def cancel_installment(
        self, installment_id: InstallmentId, reason: str, *, performer: Performer, now: datetime
    ) -> Installment:
        cleaned = clean_reason(reason)
        current = self.installment(installment_id)
        cancelled = current.cancelled(Cancellation(now, performer.user_id, cleaned))
        self.installments = tuple(
            cancelled if item.id == installment_id else item for item in self.installments
        )
        self.events.record(
            ev.InstallmentCancelled(
                shop_id=self.shop_id,
                occurred_at=now,
                performer=performer,
                entity=cancelled.entity,
                summary=f"Versement {cancelled.number} annulé ({cancelled.amount})",
                reason=cleaned,
            )
        )
        return cancelled

    def mark_written_off(
        self, reason: str, *, on: date, performer: Performer, now: datetime
    ) -> None:
        cleaned = clean_reason(reason)
        if self.status is not ReceivableStatus.OPEN:
            msg = "Seule une créance En cours peut passer en perte"
            raise InvalidStateTransition(msg, details={"status": self.status.value})
        self.write_off = WriteOff(on, cleaned, performer.user_id, now)
        self.events.record(
            ev.ReceivableWrittenOff(
                shop_id=self.shop_id,
                occurred_at=now,
                performer=performer,
                entity=self.entity,
                summary=f"Créance passée en perte : reste {self.remaining}",
                reason=cleaned,
            )
        )
