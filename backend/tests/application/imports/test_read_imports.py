"""T35 — lots : liste (modèles de l'utilisateur, M3-03), détail (auteur, éléments, lignes
refusées), rapport `errors.xlsx` (IMP-10)."""

from io import BytesIO

import pytest
from openpyxl import load_workbook

from app.application.security.errors import PermissionDenied
from app.domain.shared.errors import NotFound
from app.domain.shared.roles import Role
from tests.application.imports.cancel_support import CancelWorld

ARTICLES = "Nom;Prix de base\nPantalon;9 000\n;5 000\nPantalon;\n"


def test_list_detail_and_errors_report() -> None:
    world = CancelWorld()
    owner = world.apparel_owner()
    accountant = world.employee(owner, Role.ACCOUNTANT)
    _, articles = world.run(owner, "articles", ARTICLES)
    _, people = world.run(owner, "customers", "Nom;Téléphone\nAli;690000001\n")
    read = world.imports.http.read
    assert [b.id for b in read.list(owner)] == [people.id, articles.id]  # récent d'abord
    assert [b.id for b in read.list(accountant)] == [articles.id]  # ni clients ni créances
    with pytest.raises(NotFound):
        read.get(accountant, people.id)
    with pytest.raises(PermissionDenied):
        read.list(world.employee(owner, Role.SELLER))
    view = read.get(accountant, articles.id)
    assert (view.author_name, view.problems_total) == ("Awa", 2)
    assert view.batch.counts.rows_ignored == 2
    report = read.errors(accountant, articles.id)
    assert report.file_name == "erreurs-IMP-000001.xlsx"
    sheet = load_workbook(BytesIO(report.content)).active
    assert sheet is not None
    rows = [tuple(cell for cell in row) for row in sheet.iter_rows(values_only=True)]
    assert rows[0] == ("Ligne", "Colonne", "Problème")
    assert [row[0] for row in rows[1:]] == [3, 4]
    assert "nom" in str(rows[1][2])
    empty = read.errors(owner, people.id)
    assert len(load_workbook(BytesIO(empty.content)).active["A"]) == 1  # en-tête seul
