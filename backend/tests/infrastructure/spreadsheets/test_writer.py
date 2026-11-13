"""IMP-01 : modèle `.xlsx` relu avec `openpyxl` — feuille de saisie, en-tête « * », listes
déroulantes (stricte / indicative), feuille « Mode d'emploi » avec l'exemple ; tableau simple."""

import io

from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from app.application.imports.workbook import ChoiceList, TemplateWorkbook
from app.domain.imports.columns import ChoiceSource
from app.infrastructure.spreadsheets.reader import TabularReader
from app.infrastructure.spreadsheets.xlsx_writer import OpenpyxlWriter
from tests.infrastructure.spreadsheets.support import SPEC, WORKBOOK


def _sheet(content: bytes, name: str) -> Worksheet:
    sheet = load_workbook(io.BytesIO(content))[name]
    assert isinstance(sheet, Worksheet)
    return sheet


def test_template_sheets_header_and_instructions() -> None:
    content = OpenpyxlWriter().template(WORKBOOK)
    workbook = load_workbook(io.BytesIO(content))
    assert workbook.sheetnames == ["Articles", "Mode d'emploi", "Listes"]
    data = _sheet(content, "Articles")
    assert [c.value for c in data[1]] == ["Nom *", "Prix *", "Lieu", "Catégorie", "Type de client"]
    assert data.max_row == 1  # aucune ligne d'exemple dans la feuille de saisie
    assert data.freeze_panes == "A2"
    help_rows = [[c for c in row if c is not None] for row in _sheet(content, "Mode d'emploi")
                 .iter_rows(values_only=True)]  # fmt: skip
    flat = [str(cell) for row in help_rows for cell in row]
    assert "Mode d'emploi — modèle « Articles »" in flat
    assert "Consigne témoin" in flat
    assert ["Prix *", "Oui", "9 000", "FCFA entiers"] in help_rows
    assert ["Lieu", "Non"] in help_rows
    assert help_rows[-1][:2] == ["Chemise", "9 000"]  # ligne d'exemple complète
    assert _sheet(content, "Listes").sheet_state == "hidden"


def test_template_dropdowns_point_to_the_lists() -> None:
    content = OpenpyxlWriter().template(WORKBOOK)
    lists = _sheet(content, "Listes")
    assert [c.value for c in lists["A"] if c.value is not None] == ["Lieux", "Boutique", "Dépôt"]
    assert [c.value for c in lists["B"] if c.value is not None] == [
        "Catégories"
    ]  # aucune catégorie : pas de liste
    assert [c.value for c in lists["C"] if c.value is not None] == [
        "Types de client",
        "Particulier",
        "Entreprise",
    ]
    validations = {
        str(v.sqref): (v.formula1, v.errorStyle)
        for v in _sheet(content, "Articles").data_validations.dataValidation
    }
    assert validations == {
        "C2:C5001": ("Listes!$A$2:$A$3", "stop"),
        "E2:E5001": ("Listes!$C$2:$C$3", "stop"),
    }


def test_a_downloaded_template_is_read_back_by_the_reader() -> None:
    file_format, sheet = TabularReader().read(OpenpyxlWriter().template(WORKBOOK))
    assert file_format.extension == "xlsx"
    assert sheet.header == tuple(column.title for column in SPEC.columns)
    assert sheet.rows == ()


def test_indicative_list_warns_instead_of_refusing() -> None:
    lists = dict(WORKBOOK.lists)
    lists[ChoiceSource.CATEGORIES] = ChoiceList(
        source=ChoiceSource.CATEGORIES, title="Catégories", values=("Homme",), strict=False
    )
    content = OpenpyxlWriter().template(TemplateWorkbook(spec=SPEC, lists=lists))
    styles = {
        str(v.sqref): v.errorStyle
        for v in _sheet(content, "Articles").data_validations.dataValidation
    }
    assert styles["D2:D5001"] == "warning"


def test_simple_table() -> None:
    content = OpenpyxlWriter().table(
        "Erreurs d'import très très longues", ["Ligne", "Colonne", "Problème"],
        [[14, "Prix", "le prix est vide"]],
    )  # fmt: skip
    workbook = load_workbook(io.BytesIO(content))
    [title] = workbook.sheetnames
    assert len(title) <= 31
    rows = list(_sheet(content, title).iter_rows(values_only=True))
    assert rows == [("Ligne", "Colonne", "Problème"), (14, "Prix", "le prix est vide")]
