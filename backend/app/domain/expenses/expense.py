"""Agrégat `Expense` : dépense journalière (CDC § 11, § 20.6 ; UC-DEP-01, 04, 05).

- Numéro définitif `D-000001` attribué **à la création**, dans la transaction (RG-T05, TR-10).
- Statut Valide / Annulée. Une dépense annulée reste visible avec date, auteur et motif, et ne
  compte plus dans aucun total (RG-T03, H11) ; elle ne se corrige ni ne s'annule plus.
- Délai de correction (UC-DEP-04) : l'auteur corrige ou annule **jusqu'à minuit, heure de
  Douala, le jour de la saisie** (journée métier de `received_at`, instant serveur : l'heure du
  téléphone ne peut pas prolonger le délai) ; ensuite seul le propriétaire le peut.
"""

from dataclasses import dataclass, field, replace
from datetime import date, datetime
from enum import StrEnum

from app.domain.audit.values import EntityRef, Performer
from app.domain.expenses.details import (
    REASON_MAX_LENGTH,
    Cancellation,
    Capture,
    ExpenseDetails,
    ExpenseDraft,
)
from app.domain.expenses.errors import CorrectionWindowClosed, DescriptionRequired, ReasonRequired
from app.domain.expenses.events import ExpenseCancelled, ExpenseCorrected, ExpenseRecorded
from app.domain.expenses.ids import ExpenseId, TagId
from app.domain.shared.business_day import business_date, day_bounds_utc, require_aware
from app.domain.shared.doc_number import DocNumber, DocType
from app.domain.shared.errors import InvalidStateTransition, ValidationFailed
from app.domain.shared.events import EventCollector
from app.domain.shared.ids import ShopId
from app.domain.shops.events import diff
from app.domain.shops.expense_category import ExpenseCategory


class ExpenseStatus(StrEnum):
    VALID = "valid"
    CANCELLED = "cancelled"


def require_description(category: ExpenseCategory, details: ExpenseDetails) -> None:
    """« Autre » exige une description (UC-DEP-01) ; la catégorie porte la règle."""
    if category.id != details.category_id:
        msg = "Catégorie vérifiée différente de celle de la dépense"
        raise ValueError(msg)
    if category.requires_description and details.description is None:
        raise DescriptionRequired


def correction_deadline(received_at: datetime) -> datetime:
    """Minuit (Douala) qui suit la journée de saisie, en UTC : borne **exclue** du délai."""
    return day_bounds_utc(business_date(received_at))[1]


@dataclass(eq=False, kw_only=True)
class Expense:
    id: ExpenseId
    shop_id: ShopId
    number: DocNumber
    details: ExpenseDetails
    capture: Capture
    cancellation: Cancellation | None = None
    version: int = 0
    events: EventCollector = field(default_factory=EventCollector, repr=False)

    def __post_init__(self) -> None:
        if self.number.doc_type is not DocType.EXPENSE:
            msg = f"Numéro de dépense attendu (D-…), reçu {self.number}"
            raise ValueError(msg)

    @property
    def status(self) -> ExpenseStatus:
        return ExpenseStatus.VALID if self.cancellation is None else ExpenseStatus.CANCELLED

    @property
    def entity(self) -> EntityRef:
        return EntityRef("expense", self.id.value, str(self.number))

    @property
    def correction_deadline(self) -> datetime:
        return correction_deadline(self.capture.received_at)

    @classmethod
    def record(
        cls,
        shop_id: ShopId,
        number: DocNumber,
        details: ExpenseDetails,
        capture: Capture,
        *,
        performer: Performer,
        expense_id: ExpenseId | None = None,
    ) -> "Expense":
        expense = cls(
            id=expense_id or ExpenseId.new(),
            shop_id=shop_id,
            number=number,
            details=details,
            capture=capture,
        )
        expense.events.record(
            ExpenseRecorded(
                shop_id=shop_id,
                occurred_at=capture.received_at,
                performer=performer,
                entity=expense.entity,
                summary=f"Dépense {number} enregistrée : {details.amount} FCFA",
                captured_at=capture.captured_at,
            )
        )
        return expense

    def require_editable(self, *, by_owner: bool, now: datetime) -> None:
        """Valide, et dans le délai de l'auteur sauf pour le propriétaire (UC-DEP-04)."""
        if self.cancellation is not None:
            msg = "Cette dépense est annulée"
            raise InvalidStateTransition(msg, details={"status": self.status.value})
        if not by_owner and require_aware(now) >= self.correction_deadline:
            raise CorrectionWindowClosed(self.correction_deadline)

    def correct(self, details: ExpenseDetails, *, performer: Performer, now: datetime) -> bool:
        """Remplace le contenu ; journalise l'avant/après. `False` si rien ne change."""
        if self.cancellation is not None:
            msg = "Cette dépense est annulée"
            raise InvalidStateTransition(msg, details={"status": self.status.value})
        changes = diff(self.details.scalars(), details.scalars())
        if not changes:
            return False
        self.details = details
        self.events.record(
            ExpenseCorrected(
                shop_id=self.shop_id,
                occurred_at=now,
                performer=performer,
                entity=self.entity,
                summary=f"Dépense {self.number} modifiée",
                changes=changes,
            )
        )
        return True

    def cancel(self, reason: str, *, performer: Performer, now: datetime) -> None:
        """Annule avec motif obligatoire (UC-DEP-04, RG-T03) ; ne se défait pas."""
        if self.cancellation is not None:
            msg = "Cette dépense est déjà annulée"
            raise InvalidStateTransition(msg, details={"status": self.status.value})
        cleaned = " ".join(reason.split()) if isinstance(reason, str) else ""
        if not cleaned:
            raise ReasonRequired
        if len(cleaned) > REASON_MAX_LENGTH:
            msg = f"Motif de {REASON_MAX_LENGTH} caractères au plus"
            raise ValidationFailed(msg, details={"field": "reason"})
        self.cancellation = Cancellation(now, performer.user_id, cleaned)
        self.events.record(
            ExpenseCancelled(
                shop_id=self.shop_id,
                occurred_at=now,
                performer=performer,
                entity=self.entity,
                summary=f"Dépense {self.number} annulée",
                reason=cleaned,
            )
        )

    def retag(self, source: TagId, target: TagId) -> bool:
        """Fusion de tags : remplace `source` par `target` (sans événement, voir `MergeTags`)."""
        if source not in self.details.tag_ids:
            return False
        tags = tuple(target if tag == source else tag for tag in self.details.tag_ids)
        self.details = replace(self.details, tag_ids=tags)
        return True

    def repeat(self, today: date) -> ExpenseDraft:
        """« Refaire cette dépense » : montant, catégorie, tags, bénéficiaire, date du jour."""
        return ExpenseDraft(
            spent_on=today,
            amount=self.details.amount,
            category_id=self.details.category_id,
            tag_ids=self.details.tag_ids,
            beneficiary=self.details.beneficiary,
        )
