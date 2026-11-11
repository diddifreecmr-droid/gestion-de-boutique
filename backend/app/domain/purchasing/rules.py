"""Règles d'un achat partagées par l'agrégat (UC-ACH-03/04) : statut, délai, motif, totaux."""

from collections.abc import Sequence
from enum import StrEnum

from app.domain.purchasing.errors import ReasonRequired
from app.domain.purchasing.lines import CostedLine, PurchaseFee
from app.domain.purchasing.values import REASON_MAX_LENGTH, PurchaseDetails
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.money import Money

CORRECTION_DAYS = 7


class PurchaseStatus(StrEnum):
    VALID = "valid"
    CANCELLED = "cancelled"


def clean_reason(reason: object) -> str:
    cleaned = " ".join(reason.split()) if isinstance(reason, str) else ""
    if not cleaned:
        raise ReasonRequired
    if len(cleaned) > REASON_MAX_LENGTH:
        msg = f"Motif de {REASON_MAX_LENGTH} caractères au plus"
        raise ValidationFailed(msg, details={"field": "reason"})
    return cleaned


def check_costing(details: PurchaseDetails, costed: tuple[CostedLine, ...]) -> None:
    if tuple(line.line for line in costed) != details.lines:
        msg = "Chiffrage d'achat différent de ses lignes"
        raise ValueError(msg)


def purchase_total(costed: Sequence[CostedLine], fees: Sequence[PurchaseFee]) -> Money:
    """Total de l'achat : somme exacte des lignes et des frais (RG-T10)."""
    return Money.total(line.total for line in costed) + Money.total(fee.amount for fee in fees)
