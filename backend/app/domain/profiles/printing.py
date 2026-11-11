"""Formats de reçu et profils d'impression (CDC § 20.1 « Format de reçu », specs § 9.1).

Le format (58 mm, 80 mm, A5, A4) est un réglage de la boutique ; il désigne un **profil
d'impression** (`thermal-58`, `thermal-80`, `a4-a5`) et une mise en page par défaut que le
propriétaire peut ajuster (largeurs, marge, taille du texte, logo). Les bornes ci-dessous
refusent une mise en page absurde ; elles ne présument d'aucun modèle d'imprimante.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from app.domain.shared.errors import ValidationFailed

PAPER_WIDTH_RANGE = (40, 210)
MARGIN_RANGE = (0, 30)
FONT_SIZE_RANGE = (6, 16)


class PrintProfileCode(StrEnum):
    THERMAL_58 = "thermal-58"
    """Thermique 58 mm portable (Bluetooth) : prêt-à-porter, textile, vendeur mobile."""
    THERMAL_80 = "thermal-80"
    """Thermique 80 mm de comptoir : boutique Motos (défaut, CDC § 17.1)."""
    A4_A5 = "a4-a5"
    """Imprimante bureautique : ordinateur du propriétaire, bordereaux."""


class ReceiptFormat(StrEnum):
    MM58 = "58mm"
    MM80 = "80mm"
    A5 = "a5"
    A4 = "a4"


def _bounded(value: object, field: str, bounds: tuple[int, int]) -> int:
    low, high = bounds
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        msg = f"Valeur entre {low} et {high} attendue"
        raise ValidationFailed(msg, details={"field": field, "min": low, "max": high})
    return value


@dataclass(frozen=True, slots=True)
class PrintLayout:
    """Mise en page d'un reçu, en millimètres et en points ; validée à la construction."""

    paper_width_mm: int
    printable_width_mm: int
    margin_mm: int
    font_size_pt: int
    show_logo: bool

    def __post_init__(self) -> None:
        _bounded(self.paper_width_mm, "paper_width_mm", PAPER_WIDTH_RANGE)
        _bounded(self.printable_width_mm, "printable_width_mm", PAPER_WIDTH_RANGE)
        _bounded(self.margin_mm, "margin_mm", MARGIN_RANGE)
        _bounded(self.font_size_pt, "font_size_pt", FONT_SIZE_RANGE)
        if self.printable_width_mm > self.paper_width_mm:
            msg = "La largeur imprimable ne dépasse pas la largeur du papier"
            raise ValidationFailed(msg, details={"field": "printable_width_mm"})
        if not isinstance(self.show_logo, bool):
            msg = "Oui/Non attendu"
            raise ValidationFailed(msg, details={"field": "show_logo"})


@dataclass(frozen=True, slots=True)
class PrintProfile:
    code: PrintProfileCode
    label: str
    layout: PrintLayout


PRINT_PROFILES: Mapping[ReceiptFormat, PrintProfile] = MappingProxyType(
    {
        ReceiptFormat.MM58: PrintProfile(
            PrintProfileCode.THERMAL_58, "Thermique 58 mm", PrintLayout(58, 48, 2, 9, False)
        ),
        ReceiptFormat.MM80: PrintProfile(
            PrintProfileCode.THERMAL_80, "Thermique 80 mm", PrintLayout(80, 72, 3, 10, True)
        ),
        ReceiptFormat.A5: PrintProfile(
            PrintProfileCode.A4_A5, "Bureautique A5", PrintLayout(148, 128, 10, 11, True)
        ),
        ReceiptFormat.A4: PrintProfile(
            PrintProfileCode.A4_A5, "Bureautique A4", PrintLayout(210, 190, 10, 11, True)
        ),
    }
)
"""Profil et mise en page par défaut de chaque format (specs § 9.1)."""


def print_profile_of(receipt_format: ReceiptFormat) -> PrintProfile:
    return PRINT_PROFILES[ReceiptFormat(receipt_format)]
