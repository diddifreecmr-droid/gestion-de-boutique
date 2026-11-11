"""Versement sur créance `R-000001` (UC-CRE-03, UC-CRE-08, UC-CRE-09 ; CDC § 20.5).

- Montant > 0, mode de paiement de la boutique, référence facultative, date (RG-T09,
  vérifiée par l'application), capture (auteur, appareil, heures : RG-T04).
- Nature figée à l'enregistrement : « Normal », ou « Récupération sur perte » si la créance
  était En perte (UC-CRE-09).
- Statut Valide / Annulé (motif, propriétaire) ; un versement annulé reste visible, barré,
  et sort du total versé. `to_refund` : la vente liée a été annulée avec remboursement
  demandé (SCN-06 étape 5).
"""

from dataclasses import dataclass, replace
from datetime import date
from enum import StrEnum

from app.domain.audit.values import EntityRef
from app.domain.purchasing.values import Cancellation, Capture
from app.domain.receivables.ids import InstallmentId
from app.domain.receivables.values import require_day
from app.domain.shared.doc_number import DocNumber, DocType
from app.domain.shared.errors import InvalidAmount, InvalidStateTransition
from app.domain.shared.money import Money
from app.domain.shops.ids import PaymentModeId
from app.domain.shops.values import clean_optional

REFERENCE_MAX_LENGTH = 64


class InstallmentNature(StrEnum):
    NORMAL = "normal"
    RECOVERY = "recovery"  # Récupération sur perte


class InstallmentStatus(StrEnum):
    VALID = "valid"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True, kw_only=True)
class Installment:
    id: InstallmentId
    number: DocNumber
    paid_on: date
    amount: Money
    mode_id: PaymentModeId
    capture: Capture
    nature: InstallmentNature = InstallmentNature.NORMAL
    reference: str | None = None
    cancellation: Cancellation | None = None
    to_refund: bool = False

    def __post_init__(self) -> None:
        if self.number.doc_type is not DocType.RECEIPT:
            msg = f"Numéro de versement attendu (R-…), reçu {self.number}"
            raise ValueError(msg)
        require_day(self.paid_on, "Installment.paid_on")
        if self.amount.amount <= 0:
            msg = "Le montant d'un versement doit être supérieur à 0"
            raise InvalidAmount(msg, details={"field": "amount"})
        if not isinstance(self.mode_id, PaymentModeId):
            msg = "Installment.mode_id doit être un PaymentModeId"
            raise TypeError(msg)
        object.__setattr__(self, "nature", InstallmentNature(self.nature))
        ref = clean_optional(self.reference, "reference", max_length=REFERENCE_MAX_LENGTH)
        object.__setattr__(self, "reference", ref)

    @property
    def status(self) -> InstallmentStatus:
        return InstallmentStatus.VALID if self.cancellation is None else InstallmentStatus.CANCELLED

    @property
    def valid(self) -> bool:
        return self.cancellation is None

    @property
    def entity(self) -> EntityRef:
        return EntityRef("installment", self.id.value, str(self.number))

    def cancelled(self, cancellation: Cancellation) -> "Installment":
        if self.cancellation is not None:
            msg = "Ce versement est déjà annulé"
            raise InvalidStateTransition(msg, details={"status": self.status.value})
        return replace(self, cancellation=cancellation)

    def marked_to_refund(self) -> "Installment":
        return replace(self, to_refund=True) if self.valid else self


def total_of(installments: tuple[Installment, ...]) -> Money:
    """Total versé : versements valides seulement (UC-CRE-08)."""
    return Money.total(i.amount for i in installments if i.valid)
