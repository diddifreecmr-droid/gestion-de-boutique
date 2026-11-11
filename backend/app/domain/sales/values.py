"""Valeurs d'une vente (CDC § 20.4) : type, statut, contenu saisi, conditions de crédit, instant.

- `SaleContent` : ce que le propriétaire peut encore modifier (UC-VEN-07) — date de vente,
  client, lignes (prix et détails), paiements, note. Le lieu, le vendeur, le type et les
  articles / quantités ne changent jamais après la création.
- `CreditTerms` : date de rappel (seule date future admise, RG-T09) et conditions convenues ;
  portées par l'événement `CreditSaleRecorded` vers la créance (T17).
- `sale_instant` : instant de la vente, date des mouvements « Sortie vente ». Vente du jour →
  instant de saisie ; vente antidatée → début (00 h, Douala) de la journée choisie.
"""

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from app.domain.audit.values import Scalar
from app.domain.sales.ids import CustomerId
from app.domain.sales.lines import SaleLine
from app.domain.sales.payments import MAX_PAYMENTS, SalePayment
from app.domain.shared.business_day import business_date, day_bounds_utc, require_aware
from app.domain.shared.errors import ValidationFailed
from app.domain.shops.values import clean_optional

MAX_LINES = 50
NOTE_MAX_LENGTH = 500
TERMS_MAX_LENGTH = 500


class SaleKind(StrEnum):
    CASH = "cash"  # Comptant
    CREDIT = "credit"  # Crédit


class SaleStatus(StrEnum):
    VALID = "valid"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True, kw_only=True)
class CreditTerms:
    reminder_on: date | None = None
    terms: str | None = None

    def __post_init__(self) -> None:
        reminder = self.reminder_on
        if reminder is not None and (
            isinstance(reminder, datetime) or not isinstance(reminder, date)
        ):
            msg = "CreditTerms.reminder_on doit être une date"
            raise TypeError(msg)
        terms = clean_optional(self.terms, "credit.terms", max_length=TERMS_MAX_LENGTH)
        object.__setattr__(self, "terms", terms)


@dataclass(frozen=True, slots=True, kw_only=True)
class SaleContent:
    sold_on: date
    lines: tuple[SaleLine, ...]
    payments: tuple[SalePayment, ...] = ()
    customer_id: CustomerId | None = None
    note: str | None = None

    def __post_init__(self) -> None:
        lines, payments = tuple(self.lines), tuple(self.payments)
        if not 1 <= len(lines) <= MAX_LINES:
            msg = f"Une vente compte de 1 à {MAX_LINES} lignes"
            raise ValidationFailed(msg, details={"field": "lines"})
        if len(payments) > MAX_PAYMENTS:
            msg = f"{MAX_PAYMENTS} paiements au plus"
            raise ValidationFailed(msg, details={"field": "payments"})
        object.__setattr__(self, "lines", lines)
        object.__setattr__(self, "payments", payments)
        object.__setattr__(
            self, "note", clean_optional(self.note, "note", max_length=NOTE_MAX_LENGTH)
        )

    def scalars(self) -> dict[str, Scalar]:
        """Valeurs journalisables (avant/après, UC-VEN-07) : une clé par champ modifiable."""
        values: dict[str, Scalar] = {
            "sold_on": self.sold_on.isoformat(),
            "customer_id": None if self.customer_id is None else str(self.customer_id),
            "note": self.note,
        }
        for index, line in enumerate(self.lines, start=1):
            values[f"line_{index}_unit_price"] = line.unit_price.amount
            for rank, detail in enumerate(line.details, start=1):
                for name, value in detail.filled().items():
                    values[f"line_{index}_detail_{rank}_{name}"] = value
        for index, payment in enumerate(self.payments, start=1):
            values[f"payment_{index}_mode_id"] = str(payment.mode_id)
            values[f"payment_{index}_amount"] = payment.amount.amount
            values[f"payment_{index}_reference"] = payment.reference
        return values


def sale_instant(sold_on: date, received_at: datetime) -> datetime:
    received = require_aware(received_at)
    if business_date(received) == sold_on:
        return received
    return day_bounds_utc(sold_on)[0]
