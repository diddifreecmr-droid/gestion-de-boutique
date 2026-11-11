"""UC-STK-03, UC-STK-04, recherche et fiche (CAT-08 à CAT-13, M05 à M07, Q-14)."""

from decimal import Decimal

import pytest

from app.application.catalog.ranking import ArticleOrder, SalesRanking, SortUnavailable
from app.application.catalog.search import (
    ArticleCursor,
    ArticlePage,
    ArticlePageRequest,
    ArticleQuery,
)
from app.application.ports.uow import UnitOfWork
from app.application.security.errors import PermissionDenied
from app.domain.catalog.details import ArticleStatus
from app.domain.catalog.errors import ArticleHasStock, MinPriceAboveBase
from app.domain.catalog.prices import ArticlePrices, PriceKind
from app.domain.shared.errors import InvalidStateTransition, ValidationFailed, VersionConflict
from app.domain.shared.money import Money
from app.domain.shared.roles import Role
from tests.application.catalog.support import CatalogWorld


def test_set_prices_owner_only_with_history() -> None:
    world = CatalogWorld()
    owner = world.motos_owner()
    article = world.moto(owner, base_price=780_000)
    world.enable_min_price(owner)
    put = world.catalog.prices.execute
    new = ArticlePrices(base_price=Money(800_000), min_price=Money(720_000))
    for role in (Role.SELLER, Role.ACCOUNTANT):  # CAT-10
        with pytest.raises(PermissionDenied):
            put(world.staff(owner, role), article.id, new, 1)
    updated = put(owner, article.id, new, 1)
    assert (updated.prices.base_price, updated.version) == (Money(800_000), 2)
    with pytest.raises(VersionConflict):
        put(owner, article.id, new, 1)
    assert put(owner, article.id, new, 2).version == 2  # aucun changement : rien d'écrit
    with pytest.raises(MinPriceAboveBase):
        ArticlePrices(base_price=Money(700_000), min_price=Money(720_000))
    history = world.catalog.get.execute(owner, article.id).price_history
    assert {(h.kind, h.old_price, h.new_price) for h in history[:2]} == {
        (PriceKind.BASE, Money(780_000), Money(800_000)),
        (PriceKind.MINIMUM, None, Money(720_000)),
    }  # les plus récentes d'abord ; même instant : ordre par identifiant
    assert len(history) == 3  # CAT-08 : création (780 000) + base + minimum


def test_archive_and_reactivate() -> None:
    world = CatalogWorld()
    owner = world.motos_owner()
    article = world.moto(owner)
    stocked = world.moto(owner, model="HJ150")
    world.stock.stocked.add(stocked.id)
    with pytest.raises(ArticleHasStock):  # CAT-12
        world.catalog.archive.archive(owner, stocked.id)
    with pytest.raises(PermissionDenied):
        world.catalog.archive.archive(world.staff(owner, Role.ACCOUNTANT), article.id)
    archived = world.catalog.archive.archive(owner, article.id)
    assert archived.status is ArticleStatus.ARCHIVED
    search = world.catalog.search.execute
    active = search(owner, ArticleQuery(), ArticlePageRequest())
    assert [a.id for a in active.page.items] == [stocked.id]  # CAT-11
    every = search(owner, ArticleQuery(status=None), ArticlePageRequest())
    assert len(every.page.items) == 2
    with pytest.raises(InvalidStateTransition):
        world.catalog.archive.archive(owner, article.id)
    world.catalog.archive.reactivate(owner, article.id)  # CAT-13
    assert len(search(owner, ArticleQuery(), ArticlePageRequest()).page.items) == 2


def test_search_first_letter_accents_and_pagination() -> None:
    world = CatalogWorld()
    owner = world.motos_owner()
    catalog = (("Haojue", "HJ125-8"), ("Bajaj", "Boxer"), ("Sanili", "Éclair"), ("Haojue", "DK150"))
    for brand, model in catalog:
        world.moto(owner, model=model, brand=brand)
    search = world.catalog.search.execute

    def names(text: str | None, limit: int = 50) -> list[str]:
        found = search(owner, ArticleQuery(text), ArticlePageRequest(limit))
        return [a.display_name for a in found.page.items]

    assert names("h") == ["Haojue DK150", "Haojue HJ125-8"]  # dès la 1re lettre
    assert names("B") == ["Bajaj Boxer"]
    assert names("ECLA") == ["Sanili Éclair"]
    assert names("hj125 8") == ["Haojue HJ125-8"]
    assert names("   ") == names(None)
    first = search(owner, ArticleQuery(), ArticlePageRequest(2))
    assert first.page.next_cursor is not None
    token = first.page.next_cursor.encode()
    rest = search(owner, ArticleQuery(), ArticlePageRequest.parse(token, 2))
    assert [a.display_name for a in rest.page.items] == ["Haojue HJ125-8", "Sanili Éclair"]
    assert rest.page.next_cursor is None
    for bad in ("%%%", "YWJj"):
        with pytest.raises(ValidationFailed):
            ArticleCursor.decode(bad)
    with pytest.raises(ValidationFailed):
        ArticleQuery("x" * 101)
    with pytest.raises(ValidationFailed):
        ArticlePageRequest(0)


def test_visibility_by_role_and_driver_refused() -> None:
    world = CatalogWorld()
    owner = world.motos_owner()
    article = world.moto(owner, base_price=780_000)
    seller = world.catalog.get.execute(world.staff(owner, Role.SELLER), article.id)
    assert seller.visibility.selling_prices
    assert seller.visibility.min_prices
    assert not seller.visibility.costs
    assert seller.price_history == []
    accountant = world.catalog.get.execute(world.staff(owner, Role.ACCOUNTANT), article.id)
    assert accountant.visibility.costs
    assert not accountant.visibility.selling_prices
    assert accountant.shop_threshold == Decimal(2)
    with pytest.raises(PermissionDenied):
        world.catalog.get.execute(world.staff(owner, Role.DRIVER), article.id)


def test_best_selling_sort_is_an_extension_point() -> None:
    world = CatalogWorld()
    owner = world.motos_owner()
    with pytest.raises(SortUnavailable):
        world.catalog.search.execute(
            owner, ArticleQuery(), ArticlePageRequest(), ArticleOrder.BEST_SELLING
        )

    class Ranked(SalesRanking):
        def search(
            self, uow: UnitOfWork, query: ArticleQuery, page: ArticlePageRequest
        ) -> ArticlePage:
            return ArticlePage([], None)

    ranked = CatalogWorld(ranking=Ranked())
    found = ranked.catalog.search.execute(
        ranked.motos_owner(), ArticleQuery(), ArticlePageRequest(), ArticleOrder.BEST_SELLING
    )
    assert found.page.items == []
