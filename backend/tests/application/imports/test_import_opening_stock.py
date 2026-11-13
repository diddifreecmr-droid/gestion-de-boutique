"""T33 — import Stock de départ : SCN-L3-04 étapes 2 et 3 (P, par le comptable), mouvement
« Reprise de départ » (coût = premier CMP et dernier coût, `source = import`), article inconnu
proposé à la création, doublons même article + lieu, contrôles de ligne, Motos et Textile."""

from datetime import timedelta
from decimal import Decimal

import pytest

from app.application.catalog.ports import ARTICLE_NAME, ArticleRepository
from app.application.security.actor import Actor
from app.application.stock.ports import StockLevelRepository, StockMovementLog
from app.domain.catalog.article import Article
from app.domain.catalog.keys import identity_key
from app.domain.imports.values import ImportedEntity
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.money import Money
from app.domain.shared.roles import Role
from app.domain.stock.movement import StockMovement
from app.domain.stock.values import MovementType, SourceType
from tests.application.imports.flows import FlowWorld

HEADER = "Article;Lieu;Quantité;Coût unitaire;Date du stock\n"
STOCK = HEADER + "Pantalon;Boutique;10;9 000 FCFA;\nBoubou;Boutique;3;5 000;\n"


def article(world: FlowWorld, actor: Actor, name: str) -> Article:
    with world.core.shop_uow_factory(world.shop_of(actor)) as uow:
        found = ArticleRepository.within(uow).find_by_key(ARTICLE_NAME, identity_key(name))
    assert found is not None
    return found


def movements(world: FlowWorld, actor: Actor, found: Article) -> list[StockMovement]:
    with world.core.shop_uow_factory(world.shop_of(actor)) as uow:
        return StockMovementLog.within(uow).chronology(found.id)


def test_scn_l3_04_steps_2_and_3() -> None:
    world = FlowWorld()
    owner = world.apparel_owner()
    accountant = world.employee(owner, Role.ACCOUNTANT)
    world.run(accountant, "articles", "Nom\nPantalon\n")
    found = world.preview(accountant, "opening_stock", STOCK)
    assert (found.rows_valid, found.problems) == (2, ())
    assert found.notes == (
        "1 article nouveau sera créé",  # « Boubou » inconnu : proposé à la création
        "2 entrées « Reprise de départ » seront enregistrées",
    )
    batch, _ = world.confirm(accountant, found)
    assert str(batch.number) == "IMP-000002"
    pantalon = article(world, owner, "Pantalon")
    [entry] = movements(world, owner, pantalon)
    assert (entry.type, entry.quantity.value, entry.unit_cost) == (
        MovementType.OPENING, Decimal(10), Money(9_000),
    )  # fmt: skip
    assert (entry.source.type, entry.source.id, entry.source.number) == (
        SourceType.IMPORT, batch.id.value, "IMP-000002",
    )  # fmt: skip
    assert (pantalon.wac, pantalon.last_cost) == (Money(9_000), Money(9_000))
    boubou = article(world, owner, "Boubou")
    assert boubou.wac == Money(5_000)
    entities = sorted((i.line, i.entity) for i in batch.items)
    assert entities == [
        (2, ImportedEntity.STOCK_MOVEMENT), (3, ImportedEntity.ARTICLE),
        (3, ImportedEntity.STOCK_MOVEMENT),
    ]  # fmt: skip
    with world.core.shop_uow_factory(world.shop_of(owner)) as uow:
        [level] = StockLevelRepository.within(uow).for_article(pantalon.id)
    assert level.sellable.value == Decimal(10)
    again = world.preview(accountant, "opening_stock", STOCK)  # étape 3 : même fichier
    assert again.rows_valid == 0
    assert [p.text for p in again.problems] == [
        "Ligne 2 : doublon : stock de départ déjà importé pour « Pantalon » à Boutique",
        "Ligne 3 : doublon : stock de départ déjà importé pour « Boubou » à Boutique",
    ]
    with pytest.raises(ValidationFailed):
        world.confirm(accountant, again)
    assert len(movements(world, owner, pantalon)) == 1


def test_each_line_is_checked() -> None:
    world = FlowWorld()
    owner = world.apparel_owner()
    world.run(owner, "articles", "Nom\nPagne\n")
    tomorrow = (world.clock.today() + timedelta(days=1)).strftime("%d/%m/%Y")
    content = HEADER + (
        "Pagne;Boutique;2;1 000;\n"
        "pagne;boutique;1;1 000;\n"
        "Pagne;Lune;1;1 000;\n"
        "Pagne;Boutique;2,5;1 000;\n"
        "Pagne;Boutique;0;1 000;\n"
        f"Robe;Boutique;1;1 000;{tomorrow}\n"
        "Robe;Boutique;1;;\n"
    )
    found = world.preview(owner, "opening_stock", content)
    assert [(p.line, p.column) for p in found.problems] == [
        (3, None), (4, "Lieu"), (5, "Quantité"), (6, "Quantité"), (7, "Date du stock"),
        (8, "Coût unitaire"),
    ]  # fmt: skip
    assert found.problems[0].message == "doublon : « Pagne » à Boutique figure déjà ligne 2"
    assert found.notes == ("1 entrée « Reprise de départ » sera enregistrée",)


def test_motos_by_brand_and_model_and_textile_needs_its_articles_first() -> None:
    world = FlowWorld()
    owner = world.motos_owner()
    content = "Marque;Modèle;Lieu;Quantité;Coût unitaire\nHaojue;HJ125-8;Garoua;2;450 000\n"
    found, batch = world.run(owner, "opening_stock", content)
    assert found.notes[0] == "1 article nouveau sera créé"
    assert len(batch.items) == 2
    textile = FlowWorld()
    weaver = textile.open_profile("textile")
    content = HEADER + "Wax;Boutique;54,9;1 093;\n"
    refused = textile.preview(weaver, "opening_stock", content)
    assert refused.problems[0].message.startswith(
        "article « Wax » inconnu : importez-le d'abord avec le modèle Articles"
    )
    textile.run(weaver, "articles", "Nom;Unité\nWax;Mètre\n")
    textile.run(weaver, "opening_stock", content)
    wax = article(textile, weaver, "Wax")
    [entry] = movements(textile, weaver, wax)
    assert (str(entry.quantity.value), wax.wac) == ("54.9", Money(1_093))
