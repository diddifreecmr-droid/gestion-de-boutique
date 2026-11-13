"""Tableau lu dans un fichier et sa lecture selon les colonnes d'un modèle (UC-IMP-02).

`Sheet` : ce que rend un `SpreadsheetReader`, en-tête (ligne 1) et lignes **non vides** avec
leur numéro d'origine (une ligne blanche au milieu ne décale pas les numéros affichés).

`read_rows(columns, sheet)` :

1. en-tête vide → `IMPORT_FILE_INVALID` « la feuille est vide » ; en-têtes reconnus sans tenir
   compte de la casse, des accents ni de l'astérisque « * » ; colonne en double ou colonne
   obligatoire absente → `IMPORT_FILE_INVALID` ; colonne inconnue : ignorée ;
2. aucune ligne de données → `IMPORT_FILE_INVALID` ; plus de 5 000 → `IMPORT_TOO_MANY_ROWS` ;
3. chaque cellule est nettoyée (`ColumnSpec.clean`) ; **chaque** problème devient une
   `RowError` ; une ligne avec au moins un problème n'est pas valide (jamais importée à moitié).
"""

import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from app.domain.imports.columns import CellValue, CleanValue, ColumnSpec
from app.domain.imports.errors import ImportFileInvalid, ImportTooManyRows
from app.domain.imports.problems import CellRejected, RowError
from app.domain.imports.values import MAX_ROWS


@dataclass(frozen=True, slots=True)
class SheetRow:
    line: int
    cells: tuple[CellValue, ...]


@dataclass(frozen=True, slots=True)
class Sheet:
    header: tuple[CellValue, ...]
    rows: tuple[SheetRow, ...]


@dataclass(frozen=True, slots=True)
class ParsedRow:
    line: int
    values: Mapping[str, CleanValue]


@dataclass(frozen=True, slots=True)
class ReadRows:
    rows_read: int
    valid: tuple[ParsedRow, ...]
    errors: tuple[RowError, ...]

    @property
    def lines_in_error(self) -> int:
        return len({error.line for error in self.errors})


def fold_header(value: CellValue) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return " ".join(text.replace("*", " ").casefold().split())


def _positions(columns: Sequence[ColumnSpec], header: tuple[CellValue, ...]) -> dict[str, int]:
    if not any(fold_header(cell) for cell in header):
        reason = "la feuille est vide"
        raise ImportFileInvalid(reason)
    wanted = {fold_header(column.header): column for column in columns}
    positions: dict[str, int] = {}
    for index, cell in enumerate(header):
        column = wanted.get(fold_header(cell))
        if column is None:
            continue
        if column.key in positions:
            reason = f"colonne « {column.header} » en double"
            raise ImportFileInvalid(reason)
        positions[column.key] = index
    missing = [c.header for c in columns if c.required and c.key not in positions]
    if missing:
        reason = f"colonne « {missing[0]} » absente (télécharger le modèle)"
        raise ImportFileInvalid(reason)
    return positions


def _cell(row: SheetRow, index: int | None) -> CellValue:
    if index is None or index >= len(row.cells):
        return None
    return row.cells[index]


def read_rows(columns: Sequence[ColumnSpec], sheet: Sheet) -> ReadRows:
    positions = _positions(columns, sheet.header)
    if not sheet.rows:
        reason = "aucune ligne de données sous l'en-tête"
        raise ImportFileInvalid(reason)
    if len(sheet.rows) > MAX_ROWS:
        raise ImportTooManyRows(len(sheet.rows))
    valid: list[ParsedRow] = []
    errors: list[RowError] = []
    for row in sheet.rows:
        values: dict[str, CleanValue] = {}
        problems = []
        for column in columns:
            try:
                values[column.key] = column.clean(_cell(row, positions.get(column.key)))
            except CellRejected as rejected:
                problems.append(RowError(row.line, column.header, rejected.message))
        if problems:
            errors.extend(problems)
        else:
            valid.append(ParsedRow(row.line, MappingProxyType(values)))
    return ReadRows(len(sheet.rows), tuple(valid), tuple(errors))
