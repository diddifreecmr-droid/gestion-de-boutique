"""Registre des modèles, verdict d'un modèle et téléchargement du modèle (UC-IMP-01) : colonnes
du profil, listes déroulantes remplies avec les données de la boutique, lecture seule."""

import io
from collections.abc import Sequence

import pytest
from openpyxl import load_workbook

from app.application.imports.choices import CUSTOMER_KIND_LABELS, choice_list
from app.application.imports.models import ImportModels, ModelCheck
from app.application.imports.use_cases.preview_import import PreviewCommand
from app.application.imports.workbook import ChoiceList, TemplateWorkbook
from app.application.ports.uow import UnitOfWork
from app.application.security.actor import Actor
from app.application.security.errors import PermissionDenied
from app.bootstrap.imports import MODELS, build_imports
from app.domain.imports.columns import ChoiceSource
from app.domain.imports.problems import RowError
from app.domain.imports.sheet import ParsedRow
from app.domain.imports.template import TemplateSpec
from app.domain.profiles.profile import ShopProfile
from app.domain.sales.customer import CustomerKind
from app.domain.shared.errors import NotFound
from app.domain.shared.roles import Role
from tests.application.imports.support import NAME, PLACE, ImportWorld, WitnessArticles


def test_the_registry_is_empty_until_t33_and_refuses_twins() -> None:
    assert MODELS == ()
    with pytest.raises(NotFound):
        ImportModels().get("articles")
    with pytest.raises(ValueError, match="Deux modèles"):
        ImportModels([WitnessArticles(), WitnessArticles()])
    assert ImportModels([WitnessArticles()]).kinds == (WitnessArticles.kind,)


def test_a_line_is_either_accepted_or_refused() -> None:
    with pytest.raises(ValueError, match="à la fois"):
        ModelCheck(accepted=(2,), refused=(RowError(2, None, "doublon"),))


class Forgetful(WitnessArticles):
    def check(self, uow: UnitOfWork, actor: Actor, rows: Sequence[ParsedRow]) -> ModelCheck:
        return ModelCheck(accepted=())  # oublie les lignes reçues : bogue de modèle


class Liar(WitnessArticles):
    def template(self, profile: ShopProfile) -> TemplateSpec:
        return TemplateSpec(kind="suppliers", columns=(NAME,))  # type: ignore[arg-type]


def test_model_bugs_fail_fast() -> None:
    world = ImportWorld()
    owner = world.motos_owner()
    forgetful = build_imports(world.identity, world.storage, [Forgetful()]).http
    with pytest.raises(RuntimeError, match="n'a pas jugé"):
        forgetful.preview.execute(owner, PreviewCommand(kind="articles", content=b"Nom;Prix\na;1"))
    liar = build_imports(world.identity, world.storage, [Liar()]).http
    with pytest.raises(RuntimeError, match="autre modèle"):
        liar.template.execute(owner, "articles")
    assert world.storage.keys() == []


def test_template_download_fills_lists_from_the_shop() -> None:
    world = ImportWorld()
    owner = world.motos_owner()
    world.moto(owner, model="HJ125", category="Scooter")
    world.moto(owner, model="HJ150", category="scooter ")
    world.moto(owner, model="HJ200", category="Moto")
    before = world.table_versions()
    found = world.imports.http.template.execute(owner, "articles")
    assert world.table_versions() == before  # lecture seule
    assert found.file_name == "modele-import-articles.xlsx"
    assert found.media_type.endswith("spreadsheetml.sheet")
    workbook = load_workbook(io.BytesIO(found.content))
    assert workbook.sheetnames == ["Articles", "Mode d'emploi", "Listes"]
    columns = workbook["Listes"].iter_cols(values_only=True)
    lists = [[c for c in col if c is not None] for col in columns]
    assert lists[0][0] == "Lieux"
    assert "Garoua" in lists[0]
    assert lists[1] == ["Catégories", "Moto", "Scooter"]  # distinctes, sans la casse
    help_text = [c for row in workbook["Mode d'emploi"].iter_rows(values_only=True) for c in row]
    assert "Profil : Motos et camions" in help_text


def test_template_rights() -> None:
    world = ImportWorld()
    owner = world.motos_owner()
    with pytest.raises(PermissionDenied):
        world.imports.http.template.execute(world.staff(owner, Role.SELLER), "articles")
    with pytest.raises(NotFound):
        world.imports.http.template.execute(owner, "trucks")


def test_choice_lists() -> None:
    world = ImportWorld()
    owner = world.motos_owner()
    with world.core.shop_uow_factory(world.shop_of(owner)) as uow:
        kinds = choice_list(uow, ChoiceSource.CUSTOMER_KINDS)
        places = choice_list(uow, ChoiceSource.LOCATIONS)
        categories = choice_list(uow, ChoiceSource.CATEGORIES)
    assert (kinds.values, kinds.strict) == (("Particulier", "Entreprise"), True)
    assert CUSTOMER_KIND_LABELS["Entreprise"] is CustomerKind.COMPANY
    assert places.strict
    assert places.values
    assert not categories.strict
    assert categories.values == ()
    with pytest.raises(ValueError, match="distinctes"):
        ChoiceList(source=ChoiceSource.LOCATIONS, title="L", values=("a", "a"), strict=True)
    spec = TemplateSpec(kind=WitnessArticles.kind, columns=(NAME, PLACE))
    with pytest.raises(ValueError, match="Listes du modèle"):
        TemplateWorkbook(spec=spec)
