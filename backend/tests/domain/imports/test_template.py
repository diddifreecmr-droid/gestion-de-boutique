"""`TemplateSpec` : colonnes uniques, consignes générales communes à tous les modèles."""

import pytest

from app.domain.imports.columns import ColumnKind, ColumnSpec
from app.domain.imports.errors import ImportPreviewExpired
from app.domain.imports.template import GENERAL_INSTRUCTIONS, TemplateSpec
from app.domain.imports.values import ImportKind, SpreadsheetFormat

NAME = ColumnSpec(key="name", header="Nom", subject="le nom", required=True)


def test_sheet_title_and_instructions() -> None:
    spec = TemplateSpec(kind=ImportKind.OPENING_STOCK, columns=(NAME,), instructions=("Un lieu",))
    assert spec.sheet_title == "Stock de départ"
    assert spec.all_instructions == (*GENERAL_INSTRUCTIONS, "Un lieu")
    assert any("1 250 000" in line for line in GENERAL_INSTRUCTIONS)


@pytest.mark.parametrize(
    "columns",
    [
        (),
        (NAME, NAME),
        (NAME, ColumnSpec(key="other", header="NOM", subject="le nom")),  # même en-tête plié
    ],
)
def test_columns_must_be_present_and_distinct(columns: tuple[ColumnSpec, ...]) -> None:
    with pytest.raises(ValueError, match="Modèle"):
        TemplateSpec(kind=ImportKind.ARTICLES, columns=columns)


def test_values() -> None:
    assert ColumnSpec(key="p", header="P", subject="le p", kind="amount").kind is ColumnKind.AMOUNT  # type: ignore[arg-type]
    assert (SpreadsheetFormat.XLSX.extension, SpreadsheetFormat.CSV.extension) == ("xlsx", "csv")
    expired = ImportPreviewExpired("abc")
    assert (expired.code, expired.details) == ("IMPORT_PREVIEW_EXPIRED", {"preview_id": "abc"})
