"""Suivi d'une créance : responsable, conditions, pièces, rappels, garants (UC-CRE-01, 06, 07).

- `change` : vendeur responsable (le propriétaire seul le change : contrôlé par
  l'application, Q-21), conditions convenues, pièces jointes (identifiants) ; avant/après au
  journal, `False` si rien ne change.
- Rappels et garants : ajout et modification sur une créance non annulée ; chaque action est
  journalisée. `mark_reminder_alerted` (tâche planifiée) dépose `ReminderDue`, une fois par
  date de rappel.
"""

from dataclasses import dataclass
from datetime import date, datetime

from app.domain.audit.values import FieldChange, Performer, Scalar
from app.domain.catalog.ids import AttachmentId
from app.domain.receivables import events as ev
from app.domain.receivables.follow_up import Guarantor, Reminder, ReminderStatus
from app.domain.receivables.ids import ReminderId
from app.domain.receivables.state import ReceivableState
from app.domain.receivables.values import TERMS_MAX_LENGTH
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.ids import UserId
from app.domain.shops.events import diff
from app.domain.shops.values import clean_optional

MAX_ATTACHMENTS = 20
MAX_REMINDERS = 50
MAX_GUARANTORS = 10


@dataclass(frozen=True, slots=True, kw_only=True)
class ReceivableTerms:
    responsible_seller_id: UserId | None
    terms: str | None
    attachment_ids: tuple[AttachmentId, ...] = ()

    def __post_init__(self) -> None:
        terms = clean_optional(self.terms, "terms", max_length=TERMS_MAX_LENGTH)
        object.__setattr__(self, "terms", terms)
        attachments = tuple(dict.fromkeys(self.attachment_ids))
        if len(attachments) > MAX_ATTACHMENTS:
            msg = f"{MAX_ATTACHMENTS} pièces jointes au plus"
            raise ValidationFailed(msg, details={"field": "attachment_ids"})
        object.__setattr__(self, "attachment_ids", attachments)

    def scalars(self) -> dict[str, Scalar]:
        seller = self.responsible_seller_id
        return {
            "responsible_seller_id": None if seller is None else str(seller),
            "terms": self.terms,
            "attachment_ids": ",".join(str(a) for a in self.attachment_ids) or None,
        }


class Tracking(ReceivableState):
    @property
    def tracked_terms(self) -> ReceivableTerms:
        return ReceivableTerms(
            responsible_seller_id=self.responsible_seller_id,
            terms=self.terms,
            attachment_ids=self.attachment_ids,
        )

    def change(self, new: ReceivableTerms, *, performer: Performer, now: datetime) -> bool:
        changes = diff(self.tracked_terms.scalars(), new.scalars())
        if not changes:
            return False
        self.responsible_seller_id = new.responsible_seller_id
        self.terms = new.terms
        self.attachment_ids = new.attachment_ids
        self._audit(ev.ReceivableChanged, performer, now, "Créance modifiée", changes=changes)
        return True

    def add_reminder(self, reminder: Reminder, *, performer: Performer) -> None:
        self.require_not_cancelled()
        if len(self.reminders) >= MAX_REMINDERS:
            msg = f"{MAX_REMINDERS} rappels au plus par créance"
            raise ValidationFailed(msg, details={"field": "reminders"})
        self.reminders = (*self.reminders, reminder)
        summary = f"Rappel programmé au {reminder.remind_on.isoformat()}"
        self._audit(ev.ReminderScheduled, performer, reminder.created_at, summary)

    def change_reminder(
        self,
        reminder_id: ReminderId,
        *,
        status: ReminderStatus | None,
        remind_on: date | None,
        note: str | None,
        performer: Performer,
        now: datetime,
    ) -> Reminder:
        self.require_not_cancelled()
        before = self.reminder(reminder_id)
        after = before.changed(status=status, remind_on=remind_on, note=note)
        self._replace_reminder(after)
        changes = diff(
            {"status": before.status.value, "remind_on": before.remind_on.isoformat()},
            {"status": after.status.value, "remind_on": after.remind_on.isoformat()},
        )
        self._audit(ev.ReminderChanged, performer, now, "Rappel modifié", changes=changes)
        return after

    def mark_reminder_alerted(
        self, reminder_id: ReminderId, *, now: datetime, message: str
    ) -> None:
        reminder = self.reminder(reminder_id)
        self._replace_reminder(reminder.alerted())
        self.events.record(
            ev.ReminderDue(
                shop_id=self.shop_id,
                occurred_at=now,
                receivable_id=self.id,
                reminder_id=reminder.id,
                remind_on=reminder.remind_on,
                entity=self.entity,
                responsible_seller_id=self.responsible_seller_id,
                message=message[:500],
            )
        )

    def add_guarantor(self, guarantor: Guarantor, *, performer: Performer) -> None:
        self.require_not_cancelled()
        if len(self.guarantors) >= MAX_GUARANTORS:
            msg = f"{MAX_GUARANTORS} garants au plus par créance"
            raise ValidationFailed(msg, details={"field": "guarantors"})
        self.guarantors = (*self.guarantors, guarantor)
        summary = f"Garant ajouté : {guarantor.name}"
        self._audit(ev.GuarantorAdded, performer, guarantor.added_at, summary)

    def _replace_reminder(self, reminder: Reminder) -> None:
        self.reminders = tuple(reminder if r.id == reminder.id else r for r in self.reminders)

    def _audit(
        self,
        event: type[ev.ReceivableAuditedEvent],
        performer: Performer,
        now: datetime,
        summary: str,
        *,
        changes: tuple[FieldChange, ...] = (),
    ) -> None:
        self.events.record(
            event(
                shop_id=self.shop_id,
                occurred_at=now,
                performer=performer,
                entity=self.entity,
                summary=summary[:500],
                changes=changes,
            )
        )
