"""Suivi d'une créance : rappels (UC-CRE-06) et garants (UC-CRE-07) ; CDC § 20.5.

- **Rappel** : date (future acceptée), note facultative, statut À venir / Fait / Reporté.
  Transitions : À venir ou Reporté → Fait ; À venir ou Reporté → Reporté (nouvelle date
  obligatoire) ; Fait est final (`InvalidStateTransition`). `alerted_for` retient la date pour
  laquelle l'alerte interne est partie (tâche planifiée idempotente, TR-19) : un report
  réarme l'alerte pour la nouvelle date. Aucun message n'est envoyé au client (H19).
- **Garant** : nom et téléphone obligatoires, lien avec le client, pièce d'identité (type,
  numéro, photo = pièce jointe) visible du propriétaire et du vendeur responsable seulement.
"""

from dataclasses import dataclass, replace
from datetime import date, datetime
from enum import StrEnum

from app.domain.catalog.ids import AttachmentId
from app.domain.receivables.ids import GuarantorId, ReminderId
from app.domain.receivables.values import require_day
from app.domain.sales.customer import IdDocumentType
from app.domain.shared.business_day import require_aware
from app.domain.shared.errors import InvalidStateTransition, ValidationFailed
from app.domain.shared.ids import UserId
from app.domain.shops.values import clean_optional, clean_text

NOTE_MAX_LENGTH = 500
NAME_MAX_LENGTH = 120
PHONE_MAX_LENGTH = 32


class ReminderStatus(StrEnum):
    UPCOMING = "upcoming"  # À venir
    DONE = "done"  # Fait
    POSTPONED = "postponed"  # Reporté


@dataclass(frozen=True, slots=True, kw_only=True)
class Reminder:
    id: ReminderId
    remind_on: date
    created_by: UserId
    created_at: datetime
    note: str | None = None
    status: ReminderStatus = ReminderStatus.UPCOMING
    alerted_for: date | None = None

    def __post_init__(self) -> None:
        require_day(self.remind_on, "Reminder.remind_on")
        object.__setattr__(self, "status", ReminderStatus(self.status))
        object.__setattr__(self, "created_at", require_aware(self.created_at))
        note = clean_optional(self.note, "note", max_length=NOTE_MAX_LENGTH)
        object.__setattr__(self, "note", note)

    def is_due(self, today: date) -> bool:
        """Jour venu, pas encore fait, alerte pas encore partie pour cette date."""
        return (
            self.status is not ReminderStatus.DONE
            and self.remind_on <= today
            and self.alerted_for != self.remind_on
        )

    def changed(
        self, *, status: ReminderStatus | None, remind_on: date | None, note: str | None
    ) -> "Reminder":
        """Fait, reporté (nouvelle date) ou note corrigée ; changer la date = reporter."""
        if self.status is ReminderStatus.DONE:
            msg = "Ce rappel est déjà fait"
            raise InvalidStateTransition(msg, details={"status": self.status.value})
        wanted = None if status is None else ReminderStatus(status)
        new_date = self.remind_on if remind_on is None else require_day(remind_on, "remind_on")
        if wanted is ReminderStatus.UPCOMING and self.status is not ReminderStatus.UPCOMING:
            msg = "Un rappel reporté ne redevient pas « À venir » : reportez-le de nouveau"
            raise InvalidStateTransition(msg, details={"status": self.status.value})
        if wanted is ReminderStatus.POSTPONED and remind_on is None:
            msg = "Un report demande une nouvelle date"
            raise ValidationFailed(msg, details={"field": "remind_on"})
        target = wanted or self.status
        if new_date != self.remind_on and target is not ReminderStatus.DONE:
            target = ReminderStatus.POSTPONED
        return replace(
            self, status=target, remind_on=new_date, note=self.note if note is None else note
        )

    def alerted(self) -> "Reminder":
        return replace(self, alerted_for=self.remind_on)


@dataclass(frozen=True, slots=True, kw_only=True)
class Guarantor:
    id: GuarantorId
    name: str
    phone: str
    added_by: UserId
    added_at: datetime
    relation: str | None = None
    id_doc_type: IdDocumentType | None = None
    id_doc_number: str | None = None
    id_doc_photo_id: AttachmentId | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", clean_text(self.name, "name", max_length=NAME_MAX_LENGTH))
        phone = clean_text(self.phone, "phone", max_length=PHONE_MAX_LENGTH)
        object.__setattr__(self, "phone", phone)
        object.__setattr__(self, "relation", clean_optional(self.relation, "relation"))
        if self.id_doc_type is not None:
            object.__setattr__(self, "id_doc_type", IdDocumentType(self.id_doc_type))
        object.__setattr__(self, "id_doc_number", clean_optional(self.id_doc_number, "id_doc"))
        if self.id_doc_photo_id is not None and not isinstance(self.id_doc_photo_id, AttachmentId):
            msg = "Guarantor.id_doc_photo_id doit être un AttachmentId"
            raise TypeError(msg)
        object.__setattr__(self, "added_at", require_aware(self.added_at))
