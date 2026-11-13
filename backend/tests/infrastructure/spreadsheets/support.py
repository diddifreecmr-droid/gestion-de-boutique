"""Fichiers de test générés (aucun binaire versionné) : classeur `.xlsx` et modèle témoin."""

import io
from collections.abc import Sequence

from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from app.application.imports.workbook import ChoiceList, TemplateWorkbook
from app.domain.imports.columns import ChoiceSource, ColumnKind, ColumnSpec
from app.domain.imports.template import TemplateSpec
from app.domain.imports.values import ImportKind

COLUMNS = (
    ColumnSpec(key="name", header="Nom", subject="le nom", required=True, example="Chemise"),
    ColumnSpec(
        key="price", header="Prix", subject="le prix", kind=ColumnKind.AMOUNT, required=True,
        example="9 000", help="FCFA entiers",
    ),
    ColumnSpec(key="location", header="Lieu", subject="le lieu", choices=ChoiceSource.LOCATIONS),
    ColumnSpec(
        key="category", header="Catégorie", subject="la catégorie",
        choices=ChoiceSource.CATEGORIES,
    ),
    ColumnSpec(
        key="customer_kind", header="Type de client", subject="le type",
        choices=ChoiceSource.CUSTOMER_KINDS,
    ),
)  # fmt: skip
SPEC = TemplateSpec(kind=ImportKind.ARTICLES, columns=COLUMNS, instructions=("Consigne témoin",))
LISTS = {
    ChoiceSource.LOCATIONS: ChoiceList(
        source=ChoiceSource.LOCATIONS, title="Lieux", values=("Boutique", "Dépôt"), strict=True
    ),
    ChoiceSource.CATEGORIES: ChoiceList(
        source=ChoiceSource.CATEGORIES, title="Catégories", values=(), strict=False
    ),
    ChoiceSource.CUSTOMER_KINDS: ChoiceList(
        source=ChoiceSource.CUSTOMER_KINDS,
        title="Types de client",
        values=("Particulier", "Entreprise"),
        strict=True,
    ),
}
WORKBOOK = TemplateWorkbook(spec=SPEC, lists=LISTS)


def xlsx(rows: Sequence[Sequence[object]], *, title: str = "Articles", extra: str = "") -> bytes:
    """Classeur d'une feuille `title` (et d'une feuille `extra` placée avant, si donnée)."""
    wb = Workbook()
    ws = wb.active
    assert isinstance(ws, Worksheet)
    if extra:
        ws.title = extra
        ws.append(["ne pas lire"])
        ws = wb.create_sheet(title)
    else:
        ws.title = title
    for row in rows:
        ws.append(list(row))
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
