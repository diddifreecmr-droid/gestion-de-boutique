"""UC-STK-01 et UC-STK-02 : création, doublon proposé, référence générée, modification journalisée.

Recette CAT-01 à CAT-07, M04, M05.
"""

from decimal import Decimal

import pytest

from app.application.catalog.use_cases.context import ArticleInput
from app.application.catalog.use_cases.create_article import CreateArticleCommand
from app.application.security.errors import PermissionDenied
from app.domain.audit.values import AuditAction
from app.domain.catalog.errors import DuplicateArticle, MinPriceDisabled
from app.domain.catalog.ids import ArticleId
from app.domain.catalog.prices import ArticlePrices
from app.domain.shared.errors import ValidationFailed, VersionConflict
from app.domain.shared.money import Money
from app.domain.shared.roles import Role
from tests.application.catalog.support import CatalogWorld


def test_owner_creates_moto_with_price_and_history() -> None:
    world = CatalogWorld()
    owner = world.motos_owner()
    article = world.moto(owner, base_price=780_000, engine_cc=125)
    assert article.display_name == "Haojue HJ125-8"  # CAT-01
    assert article.prices.base_price == Money(780_000)
    sheet = world.catalog.get.execute(owner, article.id)
    [line] = sheet.price_history
    assert (line.old_price, line.new_price, line.author_id) == (None, Money(780_000), owner.user_id)
    journal = world.journal(world.shop_of(owner))
    catalog_entries = [e for e in journal if e.module == "catalog"]
    assert {e.action for e in catalog_entries} == {AuditAction.CREATE, AuditAction.UPDATE}
    assert any(e.sensitive for e in catalog_entries)  # prix fixé : sensible


def test_duplicate_is_proposed_and_creation_idempotent() -> None:
    world = CatalogWorld()
    owner = world.motos_owner()
    first = world.moto(owner)
    with pytest.raises(DuplicateArticle) as caught:  # CAT-02, variante Q-33
        world.moto(owner, model="hj125 8", brand="  HAOJUE ")
    assert caught.value.details["existing_id"] == str(first.id)
    assert caught.value.details["existing_name"] == "Haojue HJ125-8"
    wanted = ArticleId.new()
    command = CreateArticleCommand(
        data=ArticleInput(fields={"brand": "Haojue", "model": "HJ150"}), article_id=wanted
    )
    created, fresh = world.catalog.create.execute(owner, command)
    replay, again = world.catalog.create.execute(owner, command)
    assert (fresh, again, replay.id, created.id) == (True, False, wanted, wanted)


def test_accountant_creates_without_selling_price() -> None:
    world = CatalogWorld()
    owner = world.motos_owner()
    accountant = world.staff(owner, Role.ACCOUNTANT)
    article = world.moto(accountant)  # CAT-03 : sans prix → accepté
    assert article.prices.set_kinds() == frozenset()
    with pytest.raises(PermissionDenied):
        world.moto(accountant, model="HJ150", base_price=500_000)
    for role in (Role.SELLER, Role.DRIVER):
        with pytest.raises(PermissionDenied):
            world.moto(world.staff(owner, role), model="X")


def test_reference_generated_when_empty() -> None:
    world = CatalogWorld()
    owner = world.open_profile("apparel")
    create = world.catalog.create.execute
    shirt, _ = create(owner, CreateArticleCommand(data=ArticleInput(fields={"name": "Chemise"})))
    assert shirt.details.fields.reference == "REF-000001"
    manual = ArticleInput(fields={"name": "Robe", "reference": "REF-000002"})
    create(owner, CreateArticleCommand(data=manual))
    skirt, _ = create(owner, CreateArticleCommand(data=ArticleInput(fields={"name": "Jupe"})))
    assert skirt.details.fields.reference == "REF-000003"  # numéro déjà pris sauté
    taken = ArticleInput(fields={"name": "X", "reference": "ref 000001"})
    with pytest.raises(DuplicateArticle):
        create(owner, CreateArticleCommand(data=taken))
    for name in ("Jupe", "  JUPÉ ", "jupe."):  # nom unique (décision client, specs § 15.1)
        with pytest.raises(DuplicateArticle) as twice:
            create(owner, CreateArticleCommand(data=ArticleInput(fields={"name": name})))
        assert twice.value.details == {
            "existing_id": str(skirt.id),
            "existing_name": "Jupe",
            "constraint": "article_name",
        }
    with pytest.raises(DuplicateArticle):  # renommer vers un nom pris
        world.catalog.update.execute(owner, shirt.id, {"name": "jupe"}, 1, None)
    renamed = world.catalog.update.execute(owner, skirt.id, {"name": "JUPE"}, 1, None)
    assert renamed.display_name == "JUPE"  # son propre nom : pas un doublon


def test_update_logs_changes_and_checks_version() -> None:
    world = CatalogWorld()
    owner = world.motos_owner()
    accountant = world.staff(owner, Role.ACCOUNTANT)
    article = world.moto(owner)
    world.moto(owner, model="HJ150")
    update = world.catalog.update.execute
    changed = update(
        accountant, article.id, {"model": "HJ125-8A", "alert_threshold": Decimal(4)}, 1, " Typo "
    )
    assert (changed.display_name, changed.version) == ("Haojue HJ125-8A", 2)
    journal = world.journal(world.shop_of(owner))
    [entry] = [e for e in journal if e.summary.startswith("Article mod")]
    assert entry.reason == "Typo"  # CAT-05
    assert {c.field: c.after for c in entry.changes}["model"] == "HJ125-8A"
    with pytest.raises(VersionConflict):  # CAT-07
        update(owner, article.id, {"notes": "x"}, 1)
    with pytest.raises(DuplicateArticle):
        update(owner, article.id, {"model": "hj150"}, 2)
    with pytest.raises(ValidationFailed):
        update(owner, article.id, {"base_price": 1}, 2)  # prix : PUT /prices seulement
    assert update(owner, article.id, {"engine_cc": None}, 2).version == 2  # rien ne change
    with pytest.raises(PermissionDenied):
        update(world.staff(owner, Role.SELLER), article.id, {"notes": "x"}, 2)


def test_min_price_needs_setting_at_creation() -> None:
    world = CatalogWorld()
    owner = world.motos_owner()
    prices = ArticlePrices(base_price=Money(780_000), min_price=Money(720_000))
    command = CreateArticleCommand(
        data=ArticleInput(fields={"brand": "Haojue", "model": "HJ125-8"}), prices=prices
    )
    with pytest.raises(MinPriceDisabled):
        world.catalog.create.execute(owner, command)
    world.enable_min_price(owner)
    article, _ = world.catalog.create.execute(owner, command)
    assert article.prices.min_price == Money(720_000)
