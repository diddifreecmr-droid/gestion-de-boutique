"""Lecture d'un tableau selon les colonnes d'un modèle : en-têtes tolérants, erreurs « Ligne n :
… » par cellule, ligne en erreur jamais importée à moitié, 5 000 lignes au plus (IMP-04, IMP-05)."""

from datetime import date, datetime
from decimal import Decimal

import pytest

from app.domain.imports.columns import CellValue, ColumnKind, ColumnSpec
from app.domain.imports.errors import ImportFileInvalid, ImportTooManyRows
from app.domain.imports.problems import CellRejected, RowError
from app.domain.imports.sheet import Sheet, SheetRow, fold_header, read_rows

NAME = ColumnSpec(key="name", header="Nom", subject="le nom", required=True)
PRICE = ColumnSpec(
    key="price", header="Prix de vente", subject="le prix", kind=ColumnKind.AMOUNT, required=True
)
QTY = ColumnSpec(key="quantity", header="Quantité", subject="la quantité", kind=ColumnKind.NUMBER)
DAY = ColumnSpec(key="day", header="Date", subject="la date", kind=ColumnKind.DATE)
COLUMNS = (NAME, PRICE, QTY, DAY)


def sheet(header: tuple[CellValue, ...], *rows: tuple[CellValue, ...]) -> Sheet:
    return Sheet(header, tuple(SheetRow(line, cells) for line, cells in enumerate(rows, start=2)))


def test_valid_rows_are_cleaned_and_errors_name_line_and_column() -> None:
    read = read_rows(
        COLUMNS,
        sheet(
            ("NOM *", "prix de VENTE", "Quantite", "Date", "Autre"),
            ("Chemise", "9 000 FCFA", "2,5", "31/10/2026", "ignoré"),
            ("Pantalon", None, "1", None),
            (None, "12,5", "-1", "demain"),
        ),
    )
    assert read.rows_read == 3
    [row] = read.valid
    assert (row.line, dict(row.values)) == (
        2,
        {"name": "Chemise", "price": 9_000, "quantity": Decimal("2.5"), "day": date(2026, 10, 31)},
    )
    assert [e.text for e in read.errors] == [
        "Ligne 3 : le prix est vide",
        "Ligne 4 : le nom est vide",
        "Ligne 4 : le prix : montant entier attendu (FCFA, sans centimes)",
        "Ligne 4 : la quantité : le nombre ne peut pas être négatif",
        "Ligne 4 : la date : date illisible (attendu 31/10/2026)",
    ]
    assert read.errors[0] == RowError(3, "Prix de vente", "le prix est vide")
    assert read.lines_in_error == 2


@pytest.mark.parametrize(
    ("header", "reason"),
    [
        ((), "la feuille est vide"),
        ((None, " "), "la feuille est vide"),
        (("Nom",), "colonne « Prix de vente » absente (télécharger le modèle)"),
        (("Nom", "Prix de vente", "nom"), "colonne « Nom » en double"),
    ],
)
def test_unusable_headers_refuse_the_file(header: tuple[CellValue, ...], reason: str) -> None:
    with pytest.raises(ImportFileInvalid) as refused:
        read_rows(COLUMNS, sheet(header, ("a", 1)))
    assert refused.value.code == "IMPORT_FILE_INVALID"
    assert refused.value.details == {"reason": reason}


def test_a_header_without_data_is_an_empty_file() -> None:
    with pytest.raises(ImportFileInvalid, match="aucune ligne de données"):
        read_rows(COLUMNS, sheet(("Nom", "Prix de vente")))


def test_five_thousand_rows_pass_and_one_more_is_refused() -> None:
    header = ("Nom", "Prix de vente")
    rows = [("Article", 1_000)] * 5_000
    assert len(read_rows(COLUMNS, sheet(header, *rows)).valid) == 5_000
    with pytest.raises(ImportTooManyRows) as refused:
        read_rows(COLUMNS, sheet(header, *rows, ("Un de trop", 1)))
    assert refused.value.code == "IMPORT_TOO_MANY_ROWS"
    assert refused.value.details == {"max": 5_000, "rows": 5_001}


def test_short_rows_read_missing_cells_as_empty() -> None:
    read = read_rows((NAME, QTY), sheet(("Nom", "Quantité"), ("Chemise",)))
    assert dict(read.valid[0].values) == {"name": "Chemise", "quantity": None}


@pytest.mark.parametrize(
    ("kind", "raw", "expected"),
    [
        (ColumnKind.TEXT, "  Chemise   en  lin ", "Chemise en lin"),
        (ColumnKind.TEXT, 42, "42"),
        (ColumnKind.TEXT, Decimal("5.490"), "5.49"),
        (ColumnKind.TEXT, date(2026, 1, 2), "02/01/2026"),
        (ColumnKind.NUMBER, 3, Decimal(3)),
        (ColumnKind.NUMBER, "1 000,5", Decimal("1000.5")),
        (ColumnKind.DATE, datetime(2026, 3, 4, 10, 0), date(2026, 3, 4)),
        (ColumnKind.DATE, "2026-03-04", date(2026, 3, 4)),
    ],
)
def test_cleaners(kind: ColumnKind, raw: CellValue, expected: object) -> None:
    column = ColumnSpec(key="x", header="X", subject="la valeur", kind=kind)
    assert column.clean(raw) == expected


@pytest.mark.parametrize(
    ("kind", "raw", "problem"),
    [
        (ColumnKind.TEXT, "x" * 121, "la valeur : 120 caractères au plus"),
        (ColumnKind.NUMBER, "beaucoup", "la valeur : nombre illisible"),
        (ColumnKind.NUMBER, True, "la valeur : nombre illisible"),
        (ColumnKind.NUMBER, "NaN", "la valeur : nombre illisible"),
        (ColumnKind.DATE, "31/02/2026", "la valeur : date illisible (attendu 31/10/2026)"),
    ],
)
def test_cleaner_problems(kind: ColumnKind, raw: CellValue, problem: str) -> None:
    column = ColumnSpec(key="x", header="X", subject="la valeur", kind=kind)
    with pytest.raises(CellRejected) as refused:
        column.clean(raw)
    assert refused.value.message == problem


def test_column_and_problem_invariants() -> None:
    assert NAME.title == "Nom *" and QTY.title == "Quantité"
    assert fold_header(" Quantité * ") == "quantite"
    with pytest.raises(ValueError, match="snake_case"):
        ColumnSpec(key="Nom", header="Nom", subject="le nom")
    with pytest.raises(ValueError, match="en-tête et sujet"):
        ColumnSpec(key="nom", header=" ", subject="le nom")
    with pytest.raises(ValueError, match="≥ 2"):
        RowError(1, None, "en-tête")
    with pytest.raises(ValueError, match="Message"):
        RowError(2, None, " ")
    with pytest.raises(ValueError, match="message"):
        CellRejected(" ")
