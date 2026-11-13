"""Mise en forme commune des lignes lues (`.xlsx` comme `.csv`) avant le domaine.

- Valeur : texte sans blancs autour (vide → `None`), nombre d'Excel entier → `int`, décimal →
  `Decimal` (jamais de `float` : aucun arrondi caché), date et booléen tels quels, heure → texte.
- Lignes entièrement vides écartées, numéro d'origine gardé ; colonnes vides de fin retirées.
"""

from collections.abc import Iterable, Sequence
from datetime import date, time
from decimal import Decimal

from app.domain.imports.columns import CellValue
from app.domain.imports.sheet import Sheet, SheetRow


def cell_value(raw: object) -> CellValue:
    if raw is None:
        return None
    if isinstance(raw, str):
        text = raw.strip()
        return text or None
    if isinstance(raw, bool | int | Decimal | date):
        return raw
    if isinstance(raw, float):
        return int(raw) if raw.is_integer() else Decimal(str(raw))
    if isinstance(raw, time):
        return raw.isoformat(timespec="minutes")
    return str(raw).strip() or None


def _trimmed(cells: Sequence[CellValue]) -> tuple[CellValue, ...]:
    end = len(cells)
    while end and cells[end - 1] is None:
        end -= 1
    return tuple(cells[:end])


def build_sheet(rows: Iterable[Sequence[object]]) -> Sheet:
    """Ligne 1 = en-tête ; les suivantes, non vides, gardent leur numéro de ligne."""
    header: tuple[CellValue, ...] = ()
    body: list[SheetRow] = []
    for line, raw in enumerate(rows, start=1):
        cells = _trimmed([cell_value(value) for value in raw])
        if line == 1:
            header = cells
        elif cells:
            body.append(SheetRow(line, cells))
    return Sheet(header, tuple(body))
