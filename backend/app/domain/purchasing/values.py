"""Valeurs d'un achat (CDC § 20.3) : contenu saisi, capture, annulation, instant d'entrée.

- `PurchaseDetails` : fournisseur (facultatif), date d'achat (RG-T09, vérifiée par
  l'application), lieu de réception, une à `MAX_LINES` lignes (un article au plus une fois :
  la correction et le contrôle « déjà sorti » raisonnent par article x lieu), frais, n° et
  photo de facture, note.
- `Capture` : auteur, appareil, heure de l'appareil et du serveur (RG-T04).
- `entry_instant` : date de l'opération des mouvements « Entrée achat ». Achat du jour → instant
  de saisie ; achat antidaté → début (00 h, Douala) de la journée d'achat. Le grand livre et le
  rejeu du CMP sont ainsi ordonnés **par date d'achat** (RG-T11, RG-T12).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime

from app.domain.audit.values import FieldChange, Scalar
from app.domain.catalog.ids import AttachmentId
from app.domain.purchasing.ids import SupplierId
from app.domain.purchasing.lines import PurchaseFee, PurchaseLine
from app.domain.shared.business_day import business_date, day_bounds_utc, require_aware
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.ids import DeviceId, UserId
from app.domain.shops.ids import LocationId
from app.domain.shops.values import clean_optional

MAX_LINES = 100
MAX_FEES = 20
INVOICE_REF_MAX_LENGTH = 64
NOTE_MAX_LENGTH = 500
REASON_MAX_LENGTH = 500


def _text(value: object) -> str | None:
    return None if value is None else str(value)


@dataclass(frozen=True, slots=True, kw_only=True)
class PurchaseDetails:
    purchase_date: date
    location_id: LocationId
    lines: tuple[PurchaseLine, ...]
    fees: tuple[PurchaseFee, ...] = ()
    supplier_id: SupplierId | None = None
    invoice_ref: str | None = None
    invoice_photo_id: AttachmentId | None = None
    note: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.purchase_date, datetime) or not isinstance(self.purchase_date, date):
            msg = "PurchaseDetails.purchase_date doit être une date"
            raise TypeError(msg)
        if not isinstance(self.location_id, LocationId):
            msg = "PurchaseDetails.location_id doit être un LocationId"
            raise TypeError(msg)
        lines, fees = tuple(self.lines), tuple(self.fees)
        if not 1 <= len(lines) <= MAX_LINES:
            msg = f"Un achat compte de 1 à {MAX_LINES} lignes"
            raise ValidationFailed(msg, details={"field": "lines"})
        articles = [line.article_id for line in lines]
        if len(set(articles)) != len(articles):
            msg = "Un article ne figure qu'une fois dans un achat : regroupez les quantités"
            raise ValidationFailed(msg, details={"field": "lines"})
        if len(fees) > MAX_FEES:
            msg = f"{MAX_FEES} frais au plus"
            raise ValidationFailed(msg, details={"field": "fees"})
        object.__setattr__(self, "lines", lines)
        object.__setattr__(self, "fees", fees)
        ref = clean_optional(self.invoice_ref, "invoice_ref", max_length=INVOICE_REF_MAX_LENGTH)
        object.__setattr__(self, "invoice_ref", ref)
        note = clean_optional(self.note, "note", max_length=NOTE_MAX_LENGTH)
        object.__setattr__(self, "note", note)

    def scalars(self) -> dict[str, Scalar]:
        """Valeurs journalisables, une clé par champ de ligne et de frais (avant/après)."""
        values: dict[str, Scalar] = {
            "supplier_id": _text(self.supplier_id),
            "purchase_date": self.purchase_date.isoformat(),
            "location_id": str(self.location_id),
            "invoice_ref": self.invoice_ref,
            "invoice_photo_id": _text(self.invoice_photo_id),
            "note": self.note,
        }
        for index, line in enumerate(self.lines, start=1):
            values |= line.scalars(f"line_{index}")
        for index, fee in enumerate(self.fees, start=1):
            values |= fee.scalars(f"fee_{index}")
        return values


def changes_between(
    before: Mapping[str, Scalar], after: Mapping[str, Scalar]
) -> tuple[FieldChange, ...]:
    """Avant/après sur l'union des clés (ligne ajoutée ou retirée : `None` de l'autre côté)."""
    keys = list(before) + [key for key in after if key not in before]
    return tuple(
        FieldChange(key, before.get(key), after.get(key))
        for key in keys
        if before.get(key) != after.get(key)
    )


@dataclass(frozen=True, slots=True)
class Capture:
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
    """« Annulé le … par … — motif : … » (UC-ACH-04, RG-T03)."""

    at: datetime
    by: UserId
    reason: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "at", require_aware(self.at))
        if not isinstance(self.by, UserId):
            msg = "Cancellation.by doit être un UserId"
            raise TypeError(msg)


def entry_instant(purchase_date: date, received_at: datetime) -> datetime:
    """Date de l'opération des entrées de stock d'un achat (voir l'en-tête du module)."""
    received = require_aware(received_at)
    if business_date(received) == purchase_date:
        return received
    return day_bounds_utc(purchase_date)[0]
