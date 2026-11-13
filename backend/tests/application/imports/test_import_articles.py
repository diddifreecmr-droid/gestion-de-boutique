"""T33 — import Articles : SCN-L3-04 étape 1 (P, par le comptable), prix réservés au
propriétaire, colonnes et champs des profils Motos et Textile, confirmation idempotente
(IMP-09), une seule transaction, journal (AUD-L3-01)."""

from datetime import timedelta

import pytest

from app.application.catalog.ports import ArticleRepository
from app.application.catalog.search import ArticlePageRequest, ArticleQuery
from app.application.catalog.use_cases.context import ArticleInput
from app.application.catalog.use_cases.create_article import CreateArticleCommand
from app.application.imports.access import shop_profile
from app.application.security.actor import Actor
from app.application.security.errors import PermissionDenied
from app.domain.audit.values import AuditAction
from app.domain.catalog.article import Article
from app.domain.imports.errors import ImportPreviewExpired
from app.domain.imports.values import ImportedEntity, ImportKind
from app.domain.profiles.profile import ShopProfile
from app.domain.shared.errors import NotFound, ValidationFailed
from app.domain.shared.money import Money
from app.domain.shared.quantity import StockUnit
from app.domain.shared.roles import Role
from tests.application.imports.flows import FlowWorld

ARTICLES = "Nom;Catégorie;Prix de vente\nChemise;Haut;\nPantalon;Bas;\nRobe;;\n;Haut;\n"


def articles(world: FlowWorld, actor: Actor) -> dict[str, Article]:
    with world.core.shop_uow_factory(world.shop_of(actor)) as uow:
        page = ArticleRepository.within(uow).search(ArticleQuery(), ArticlePageRequest(100))
    return {article.display_name: article for article in page.items}


def chemise(world: FlowWorld, owner: Actor) -> None:
    command = CreateArticleCommand(data=ArticleInput(fields={"name": "Chemise"}))
    world.catalog.create.execute(owner, command)


def test_scn_l3_04_step_1_by_the_accountant() -> None:
    world = FlowWorld()
    owner = world.apparel_owner()
    chemise(world, owner)
    accountant = world.employee(owner, Role.ACCOUNTANT)
    found = world.preview(accountant, "articles", ARTICLES)
    assert (found.rows_read, found.rows_valid, found.rows_ignored) == (4, 2, 2)
    assert [p.text for p in found.problems] == [
        "Ligne 2 : doublon : l'article « Chemise » existe déjà",
        "Ligne 5 : le nom est vide",
    ]
    assert found.notes == ("2 articles nouveaux seront créés",)
    assert set(articles(world, owner)) == {"Chemise"}  # l'aperçu n'écrit rien
    batch, created = world.confirm(accountant, found)
    assert created
    assert (str(batch.number), batch.kind, batch.counts.rows_imported) == (
        "IMP-000001", ImportKind.ARTICLES, 2,
    )  # fmt: skip
    assert batch.counts.rows_ignored == 2
    stored = articles(world, owner)
    assert set(stored) == {"Chemise", "Pantalon", "Robe"}
    assert [stored[n].details.fields.reference for n in ("Pantalon", "Robe")] == [
        "REF-000002", "REF-000003",
    ]  # fmt: skip  # « Chemise » (écran) a pris REF-000001
    assert stored["Pantalon"].details.fields.attributes == {"category": "Bas"}
    assert [(i.line, i.entity) for i in batch.items] == [
        (3, ImportedEntity.ARTICLE), (4, ImportedEntity.ARTICLE),
    ]  # fmt: skip
    journal = world.journal(world.shop_of(owner))
    imported = [e for e in journal if e.action is AuditAction.IMPORT]
    assert [e.entity.number for e in imported] == ["IMP-000001"]
    assert sum(1 for e in journal if e.entity.type == "article") == 3


def test_prices_are_reserved_to_the_owner() -> None:
    world = FlowWorld()
    owner = world.apparel_owner()
    accountant = world.employee(owner, Role.ACCOUNTANT)
    content = "Nom;Prix de vente;Prix minimum\nJupe;12 000;10 000\nVeste;5 000;6 000\n"
    refused = world.preview(accountant, "articles", content)
    assert [p.column for p in refused.problems] == ["Prix de vente", "Prix de vente"]
    assert refused.problems[0].message.startswith("les prix sont fixés par le propriétaire")
    disabled = world.preview(owner, "articles", content)  # réglage « prix minimum » éteint
    assert [p.column for p in disabled.problems] == ["Prix minimum", "Prix minimum"]
    world.enable_min_price(owner)
    found, _ = world.run(owner, "articles", content)
    assert [p.text for p in found.problems] == [
        "Ligne 3 : le prix minimum ne peut pas dépasser le prix de base",
    ]
    jupe = articles(world, owner)["Jupe"]
    assert (jupe.prices.base_price, jupe.prices.min_price) == (Money(12_000), Money(10_000))


def test_motos_and_textile_fields_come_from_the_profile() -> None:
    world = FlowWorld()
    owner = world.motos_owner()
    model = world.imports.models.get("articles")
    columns = [c.title for c in model.template(owner_profile(world, owner)).columns]
    assert columns[:3] == ["Marque *", "Modèle *", "Cylindrée (cm³)"]
    found, _ = world.run(
        owner,
        "articles",
        "Marque;Modèle;Cylindrée (cm³)\nHaojue;HJ125-8;125\nHaojue;HJ125-8;\nTVS;;\n",
    )
    assert [p.text for p in found.problems] == [
        "Ligne 3 : doublon : « Haojue HJ125-8 » figure déjà ligne 2",
        "Ligne 4 : le modèle est vide",
    ]
    moto = articles(world, owner)["Haojue HJ125-8"]
    assert moto.details.fields.attributes == {"engine_cc": 125}
    textile = FlowWorld()
    weaver = textile.open_profile("textile")
    content = (
        "Nom;Unité;Vente à la pièce;Longueur d'une pièce (m);Prix à la pièce\n"
        "Wax;Mètre;Oui;5,49;27 000\nBasin;Kilo;;;\nBazin;Pièce;peut-être;;\n"
    )
    found, _ = textile.run(weaver, "articles", content)
    assert [(p.line, p.column) for p in found.problems] == [(3, "Unité"), (4, "Vente à la pièce")]
    wax = articles(textile, weaver)["Wax"]
    assert wax.details.fields.stock_unit is StockUnit.METER
    assert wax.details.fields.sold_by_piece
    assert str(wax.details.fields.piece_length_m) == "5.49"
    assert wax.prices.base_price_piece == Money(27_000)


def owner_profile(world: FlowWorld, owner: Actor) -> ShopProfile:
    with world.core.shop_uow_factory(world.shop_of(owner)) as uow:
        return shop_profile(uow)


def test_confirmation_is_idempotent_and_guarded() -> None:
    world = FlowWorld()
    owner = world.apparel_owner()
    found, batch = world.run(owner, "articles", "Nom\nPagne\n")
    later = world.clock.now() + timedelta(hours=2)
    world.clock.move_to(later)
    again, created = world.confirm(owner, found)  # IMP-09 : même lot, même après 30 minutes
    assert (again.id, created) == (batch.id, False)
    assert set(articles(world, owner)) == {"Pagne"}
    stale = world.preview(owner, "articles", "Nom\nBoubou\n")
    world.clock.move_to(later + timedelta(minutes=31))
    with pytest.raises(ImportPreviewExpired):
        world.confirm(owner, stale)
    seller = world.employee(owner, Role.SELLER)
    with pytest.raises(PermissionDenied):
        world.preview(seller, "articles", "Nom\nBoubou\n")
    accountant = world.employee(owner, Role.ACCOUNTANT)
    with pytest.raises(NotFound):  # l'aperçu, ou le lot, d'un autre utilisateur
        world.confirm(accountant, found)


def test_nothing_valid_writes_nothing() -> None:
    world = FlowWorld()
    owner = world.apparel_owner()
    world.run(owner, "articles", "Nom\nPagne\n")
    before = world.journal(world.shop_of(owner))
    replay = world.preview(owner, "articles", "Nom\nPagne\n;\n")
    with pytest.raises(ValidationFailed) as refused:
        world.confirm(owner, replay)
    assert refused.value.details["field"] == "preview_id"
    assert world.journal(world.shop_of(owner)) == before
