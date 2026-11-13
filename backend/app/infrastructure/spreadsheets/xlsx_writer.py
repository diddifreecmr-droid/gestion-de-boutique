"""`SpreadsheetWriter` avec `openpyxl` : modèle d'import et tableau simple (IMP-01, IMP-10).

Modèle, dans cet ordre (la lecture prend la première feuille de saisie) :

1. feuille de saisie (« Articles »…) : en-tête en gras (« Nom * » si obligatoire), volet figé,
   listes déroulantes sur les lignes 2 à 5 001 (stricte : refus hors liste ; indicative :
   avertissement seulement) ;
2. « Mode d'emploi » : consignes, une ligne par colonne (obligatoire, exemple, aide), puis une
   ligne d'exemple complète (jamais dans la feuille de saisie : elle serait importée) ;
3. « Listes » (masquée) : une colonne par liste déroulante, source des validations.
"""

import io
from collections.abc import Sequence

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.worksheet import Worksheet

from app.application.imports.ports import SpreadsheetWriter
from app.application.imports.workbook import ChoiceList, TemplateWorkbook
from app.domain.imports.columns import CellValue
from app.domain.imports.values import MAX_ROWS

INSTRUCTIONS_TITLE = "Mode d'emploi"
LISTS_TITLE = "Listes"
_BOLD = Font(bold=True)
_HEADER_FILL = PatternFill("solid", fgColor="DDE7F0")
_LAST_ROW = MAX_ROWS + 1


def _header(ws: Worksheet, titles: Sequence[str]) -> None:
    ws.append(list(titles))
    for index, title in enumerate(titles, start=1):
        cell = ws.cell(row=1, column=index)
        cell.font, cell.fill = _BOLD, _HEADER_FILL
        ws.column_dimensions[get_column_letter(index)].width = max(14, len(title) + 4)
    ws.freeze_panes = "A2"


def _lists_sheet(wb: Workbook, lists: Sequence[ChoiceList]) -> dict[str, str]:
    """Écrit les listes ; renvoie source → plage absolue (`Listes!$A$2:$A$4`)."""
    ws = wb.create_sheet(LISTS_TITLE)
    ranges: dict[str, str] = {}
    for index, choice in enumerate(lists, start=1):
        letter = get_column_letter(index)
        ws.cell(row=1, column=index, value=choice.title).font = _BOLD
        for row, value in enumerate(choice.values, start=2):
            ws.cell(row=row, column=index, value=value)
        if choice.values:
            last = len(choice.values) + 1
            ranges[choice.source.value] = f"{LISTS_TITLE}!${letter}$2:${letter}${last}"
    ws.sheet_state = "hidden"
    return ranges


def _validations(ws: Worksheet, workbook: TemplateWorkbook, ranges: dict[str, str]) -> None:
    for index, column in enumerate(workbook.spec.columns, start=1):
        if column.choices is None or column.choices.value not in ranges:
            continue
        strict = workbook.lists[column.choices].strict
        validation = DataValidation(
            type="list",
            formula1=ranges[column.choices.value],  # sans « = » : forme stockée par Excel
            allow_blank=True,
            showErrorMessage=True,
            errorStyle="stop" if strict else "warning",
            errorTitle=column.header,
            error="Choisir une valeur de la liste" if strict else "Valeur hors de la liste",
        )
        letter = get_column_letter(index)
        validation.add(f"{letter}2:{letter}{_LAST_ROW}")
        ws.add_data_validation(validation)


def _instructions(wb: Workbook, workbook: TemplateWorkbook) -> None:
    spec = workbook.spec
    ws = wb.create_sheet(INSTRUCTIONS_TITLE)
    ws.append([f"Mode d'emploi — modèle « {spec.kind.label} »"])
    ws.cell(row=1, column=1).font = Font(bold=True, size=14)
    for line in spec.all_instructions:
        ws.append([line])
    ws.append([])
    ws.append(["Colonne", "Obligatoire", "Exemple", "Aide"])
    for column in spec.columns:
        ws.append([column.title, "Oui" if column.required else "Non", column.example, column.help])
    ws.append([])
    ws.append(["Exemple de ligne"])
    ws.append([column.title for column in spec.columns])
    ws.append([column.example for column in spec.columns])
    ws.column_dimensions["A"].width = 40
    for letter in ("B", "C", "D"):
        ws.column_dimensions[letter].width = 24


def _saved(wb: Workbook) -> bytes:
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


class OpenpyxlWriter(SpreadsheetWriter):
    def template(self, workbook: TemplateWorkbook) -> bytes:
        wb = Workbook()
        data = wb.active
        if not isinstance(data, Worksheet):  # classeur neuf : toujours une feuille de calcul
            msg = "openpyxl : feuille active absente d'un classeur neuf"
            raise TypeError(msg)
        data.title = workbook.spec.sheet_title
        _header(data, [column.title for column in workbook.spec.columns])
        _instructions(wb, workbook)
        if workbook.lists:
            sources = [c.choices for c in workbook.spec.columns if c.choices is not None]
            ordered = [workbook.lists[source] for source in dict.fromkeys(sources)]  # ordre des colonnes
            _validations(data, workbook, _lists_sheet(wb, ordered))
        return _saved(wb)

    def table(
        self, title: str, header: Sequence[str], rows: Sequence[Sequence[CellValue]]
    ) -> bytes:
        wb = Workbook()
        ws = wb.active
        if not isinstance(ws, Worksheet):
            msg = "openpyxl : feuille active absente d'un classeur neuf"
            raise TypeError(msg)
        ws.title = title[:31]
        _header(ws, header)
        for row in rows:
            ws.append(list(row))
        return _saved(wb)
