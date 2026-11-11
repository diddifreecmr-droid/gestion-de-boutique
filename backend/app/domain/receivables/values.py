"""Valeurs d'une créance (CDC § 10.1, § 20.5) : origine, statut, mise en perte, ancienneté.

- Statut **calculé** (`Receivable.status`) : Annulée (vente liée annulée) > En perte (déclarée
  par le propriétaire) > Soldée (reste = 0) > En cours (reste > 0).
- Ancienneté en jours depuis la date d'ouverture ; classes UC-CRE-04 tranchées (**Q-19**) :
  0 à 30 jours → « moins de 30 » (30 jours exactement y reste), 31-60, 61-90, plus de 90.
"""

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from app.domain.shared.business_day import require_aware
from app.domain.shared.ids import UserId

DESCRIPTION_MAX_LENGTH = 500
TERMS_MAX_LENGTH = 500
REASON_MAX_LENGTH = 500


class ReceivableOrigin(StrEnum):
    SALE = "sale"  # Vente
    LEGACY = "legacy"  # Ancienne (UC-CRE-02)


class ReceivableStatus(StrEnum):
    OPEN = "open"  # En cours
    SETTLED = "settled"  # Soldée
    CANCELLED = "cancelled"  # Annulée
    WRITTEN_OFF = "written_off"  # En perte


class SeniorityBand(StrEnum):
    UNDER_30 = "under_30"
    FROM_31_TO_60 = "31_60"
    FROM_61_TO_90 = "61_90"
    OVER_90 = "over_90"


def seniority_band(days: int) -> SeniorityBand:
    """Classe d'ancienneté (Q-19 : 30 jours → « moins de 30 », 31 → « 31-60 »)."""
    if days <= 30:
        return SeniorityBand.UNDER_30
    if days <= 60:
        return SeniorityBand.FROM_31_TO_60
    if days <= 90:
        return SeniorityBand.FROM_61_TO_90
    return SeniorityBand.OVER_90


def require_day(value: object, name: str) -> date:
    if isinstance(value, datetime) or not isinstance(value, date):
        msg = f"{name} doit être une date"
        raise TypeError(msg)
    return value


@dataclass(frozen=True, slots=True)
class WriteOff:
    """Mise en perte (UC-CRE-09) : date, motif, auteur, instant."""

    on: date
    reason: str
    by: UserId
    at: datetime

    def __post_init__(self) -> None:
        require_day(self.on, "WriteOff.on")
        object.__setattr__(self, "at", require_aware(self.at))


@dataclass(frozen=True, slots=True)
class SaleCancellation:
    """Annulation de la vente liée (UC-VEN-08) : jour (Douala) et instant."""

    on: date
    at: datetime

    def __post_init__(self) -> None:
        require_day(self.on, "SaleCancellation.on")
        object.__setattr__(self, "at", require_aware(self.at))
