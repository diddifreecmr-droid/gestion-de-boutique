"""Valeurs d'une dépense (CDC § 20.6) : contenu saisi, capture, annulation, brouillon.

- `ExpenseDetails` : ce que l'auteur saisit ou corrige. Montant **entier strictement positif**
  (FCFA, TR-06), catégorie et mode de paiement obligatoires, tags sans doublon (ordre gardé),
  description, lieu, bénéficiaire et justificatif facultatifs. La règle « Autre exige une
  description » dépend de la catégorie : `require_description` (dans `expense.py`).
- `Capture` : qui a saisi, depuis quel appareil, quand (appareil et serveur, RG-T04, TR-07,
  TR-11 : gardés pour la saisie hors ligne, aujourd'hui désactivée).
- `ExpenseDraft` : formulaire pré-rempli de « Refaire cette dépense » (UC-DEP-05).
"""

from dataclasses import dataclass
from datetime import date, datetime

from app.domain.audit.values import Scalar
from app.domain.expenses.ids import AttachmentId, TagId
from app.domain.shared.business_day import require_aware
from app.domain.shared.errors import InvalidAmount
from app.domain.shared.ids import DeviceId, UserId
from app.domain.shared.money import BIGINT_MAX
from app.domain.shops.ids import ExpenseCategoryId, LocationId, PaymentModeId
from app.domain.shops.values import clean_optional

DESCRIPTION_MAX_LENGTH = 500
BENEFICIARY_MAX_LENGTH = 120
REASON_MAX_LENGTH = 500


def positive_amount(value: object) -> int:
    """Montant de dépense : entier > 0 (CDC § 20.6 « supérieur à 0 ») ; `InvalidAmount` sinon."""
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"Le montant doit être un int (FCFA entiers), reçu {type(value).__name__}"
        raise TypeError(msg)
    if not 0 < value <= BIGINT_MAX:
        msg = "Le montant doit être supérieur à 0"
        raise InvalidAmount(msg, details={"field": "amount"})
    return value


def _require(value: object, kind: type, name: str, *, optional: bool = False) -> None:
    if value is None and optional:
        return
    if not isinstance(value, kind):
        msg = f"ExpenseDetails.{name} doit être un {kind.__name__}"
        raise TypeError(msg)


@dataclass(frozen=True, slots=True, kw_only=True)
class ExpenseDetails:
    spent_on: date
    amount: int
    category_id: ExpenseCategoryId
    payment_mode_id: PaymentModeId
    tag_ids: tuple[TagId, ...] = ()
    description: str | None = None
    location_id: LocationId | None = None
    beneficiary: str | None = None
    attachment_id: AttachmentId | None = None

    def __post_init__(self) -> None:
        if isinstance(self.spent_on, datetime) or not isinstance(self.spent_on, date):
            msg = "ExpenseDetails.spent_on doit être une date"
            raise TypeError(msg)
        positive_amount(self.amount)
        _require(self.category_id, ExpenseCategoryId, "category_id")
        _require(self.payment_mode_id, PaymentModeId, "payment_mode_id")
        _require(self.location_id, LocationId, "location_id", optional=True)
        _require(self.attachment_id, AttachmentId, "attachment_id", optional=True)
        tags = tuple(dict.fromkeys(self.tag_ids))
        for tag in tags:
            _require(tag, TagId, "tag_ids")
        object.__setattr__(self, "tag_ids", tags)
        object.__setattr__(
            self,
            "description",
            clean_optional(self.description, "description", max_length=DESCRIPTION_MAX_LENGTH),
        )
        object.__setattr__(
            self,
            "beneficiary",
            clean_optional(self.beneficiary, "beneficiary", max_length=BENEFICIARY_MAX_LENGTH),
        )

    def scalars(self) -> dict[str, Scalar]:
        """Valeurs journalisables (avant/après d'une correction, UC-JRN-02)."""

        def text(value: object) -> str | None:
            return None if value is None else str(value)

        return {
            "spent_on": self.spent_on.isoformat(),
            "amount": self.amount,
            "category_id": str(self.category_id),
            "payment_mode_id": str(self.payment_mode_id),
            "tag_ids": ",".join(sorted(str(tag) for tag in self.tag_ids)),
            "description": self.description,
            "location_id": text(self.location_id),
            "beneficiary": self.beneficiary,
            "attachment_id": text(self.attachment_id),
        }


@dataclass(frozen=True, slots=True)
class Capture:
    """Saisie : auteur (`created_by`), appareil, instant appareil puis instant serveur."""

    created_by: UserId
    device_id: DeviceId
    captured_at: datetime
    received_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.created_by, UserId) or not isinstance(self.device_id, DeviceId):
            msg = "Capture exige un UserId et un DeviceId"
            raise TypeError(msg)
        object.__setattr__(self, "captured_at", require_aware(self.captured_at))
        object.__setattr__(self, "received_at", require_aware(self.received_at))


@dataclass(frozen=True, slots=True)
class Cancellation:
    """« Annulée le … par … — motif : … » (RG-T03, H11)."""

    at: datetime
    by: UserId
    reason: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "at", require_aware(self.at))
        if not isinstance(self.by, UserId):
            msg = "Cancellation.by doit être un UserId"
            raise TypeError(msg)


@dataclass(frozen=True, slots=True, kw_only=True)
class ExpenseDraft:
    """Brouillon de « Refaire cette dépense » : rien n'est enregistré (UC-DEP-05)."""

    spent_on: date
    amount: int
    category_id: ExpenseCategoryId
    tag_ids: tuple[TagId, ...]
    beneficiary: str | None
