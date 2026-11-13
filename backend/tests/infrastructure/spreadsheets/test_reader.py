"""`SpreadsheetReader` : `.xlsx` et `.csv` (virgule, point-virgule, UTF-8 avec ou sans BOM,
Windows-1252) donnent le même tableau (IMP-06) ; fichiers illisibles refusés avec la raison
(IMP-05) ; lignes vides écartées sans décaler les numéros."""

from datetime import datetime
from decimal import Decimal

import pytest

from app.domain.imports.errors import ImportFileInvalid
from app.domain.imports.sheet import Sheet, SheetRow, read_rows
from app.domain.imports.values import SpreadsheetFormat
from app.infrastructure.spreadsheets.reader import OLE_SIGNATURE, TabularReader
from app.infrastructure.spreadsheets.rows import cell_value
from tests.infrastructure.spreadsheets.support import COLUMNS, xlsx

EXPECTED = Sheet(
    ("Nom", "Prix"),
    (SheetRow(2, ("Chemise", "9 000")), SheetRow(4, ("Pagne wax", "1 250 000 FCFA"))),
)
CSV_TEXT = "Nom;Prix\nChemise;9 000\n;\nPagne wax;1 250 000 FCFA\n"


@pytest.mark.parametrize(
    "content",
    [
        CSV_TEXT.encode("utf-8"),
        b"\xef\xbb\xbf" + CSV_TEXT.encode("utf-8"),
        CSV_TEXT.replace(";", ",").encode("utf-8"),
        CSV_TEXT.replace("\n", "\r\n").encode("cp1252"),
    ],
    ids=["utf8-point-virgule", "utf8-bom", "virgule", "windows-1252-crlf"],
)
def test_csv_variants_give_the_same_sheet(content: bytes) -> None:
    assert TabularReader().read(content) == (SpreadsheetFormat.CSV, EXPECTED)


def test_quoted_csv_keeps_commas_inside_cells() -> None:
    content = 'Nom,Prix\n"Pagne, wax","1,00"\n'.encode()
    _, sheet = TabularReader().read(content)
    assert sheet.rows == (SheetRow(2, ("Pagne, wax", "1,00")),)


def test_accented_windows_csv_is_decoded() -> None:
    _, sheet = TabularReader().read("Nom;Catégorie\nRobe;Été\n".encode("cp1252"))
    assert sheet.header == ("Nom", "Catégorie") and sheet.rows[0].cells == ("Robe", "Été")


def test_xlsx_gives_the_same_sheet_with_typed_cells() -> None:
    content = xlsx([["Nom", "Prix"], ["Chemise", "9 000"], [None, None], ["Pagne wax", "1 250 000 FCFA"]])
    assert TabularReader().read(content) == (SpreadsheetFormat.XLSX, EXPECTED)
    typed = xlsx([["Nom", "Prix", "Le", None], ["Chemise", 9000.0, datetime(2026, 1, 2), None],
                  ["Robe", 12.5, True]])  # fmt: skip
    _, sheet = TabularReader().read(typed)
    assert sheet.header == ("Nom", "Prix", "Le")
    assert sheet.rows[0].cells == ("Chemise", 9000, datetime(2026, 1, 2))
    assert sheet.rows[1].cells == ("Robe", Decimal("12.5"), True)


def test_xlsx_skips_the_help_sheets_and_reads_the_input_sheet() -> None:
    content = xlsx([["Nom", "Prix"], ["Chemise", 9000]], extra="Mode d'emploi")
    _, sheet = TabularReader().read(content)
    assert sheet.rows == (SheetRow(2, ("Chemise", 9000)),)
    read = read_rows(COLUMNS, sheet)
    assert dict(read.valid[0].values)["price"] == 9000


@pytest.mark.parametrize(
    ("content", "reason"),
    [
        (OLE_SIGNATURE + b"\x00" * 64, "format .xls (Excel 97-2003) non pris en charge"),
        (b"PK\x03\x04pas une archive", "fichier Excel illisible"),
        (b"%PDF-1.7", "ce n'est pas un tableur"),
        (b"\x89PNG\r\n\x1a\n", "ce n'est pas un tableur"),
        ("Nom;Prix".encode("utf-16"), "fichier illisible"),
        (b"Nom;Prix\n\x81\x8d;1\n", "encodage du fichier CSV non reconnu"),
        (xlsx([["x"]], title="Mode d'emploi"), "aucune feuille de saisie"),
    ],
    ids=["xls", "zip-corrompu", "pdf", "png", "utf16", "encodage", "sans-feuille"],
)
def test_unreadable_files_are_refused_with_a_reason(content: bytes, reason: str) -> None:
    with pytest.raises(ImportFileInvalid) as refused:
        TabularReader().read(content)
    assert refused.value.code == "IMPORT_FILE_INVALID"
    assert str(refused.value.details["reason"]).startswith(reason)


def test_malformed_csv_is_refused() -> None:
    with pytest.raises(ImportFileInvalid, match="CSV mal formé"):
        TabularReader().read(b'Nom;Prix\n"Chemise;1\n')  # guillemet jamais refermé


def test_cell_values() -> None:
    assert cell_value("  ") is None and cell_value(" a ") == "a"
    assert cell_value(2.0) == 2 and cell_value(0.1) == Decimal("0.1")
    assert cell_value(datetime(2026, 1, 1, 9, 5).time()) == "09:05"
    assert cell_value(object()) is not None
