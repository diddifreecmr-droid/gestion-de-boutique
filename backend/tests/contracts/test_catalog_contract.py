"""Contrat des dépôts du catalogue (T13) : aller-retour, unicités, recherche, isolation, verrou."""

import pytest

from app.application.catalog.ports import (
    ARTICLE_BRAND_MODEL,
    ARTICLE_NAME,
    ARTICLE_REFERENCE,
    ArticleRepository,
    PriceHistoryLog,
)
from app.application.catalog.search import ArticlePageRequest, ArticleQuery
from app.application.ports.errors import IsolationViolation
from app.domain.catalog.article import Article
from app.domain.catalog.details import ArticleStatus
from app.domain.shared.errors import Duplicate, NotFound, VersionConflict
from app.domain.shared.ids import ShopId
from tests.contracts.backends import ContractBackend
from tests.contracts.catalog_data import apparel, history, moto, wax
from tests.contracts.helpers import run_in_uow


def test_article_round_trip(backend: ContractBackend, shop_a: ShopId) -> None:
    written = [moto(shop_a), wax(shop_a)]
    with backend.uow(shop_a) as uow:
        for article in written:
            ArticleRepository.within(uow).add(article)
        uow.commit()
    with backend.uow(shop_a) as uow:
        read = [ArticleRepository.within(uow).get(article.id) for article in written]
    for before, after in zip(written, read, strict=True):
        assert after.details == before.details
        assert after.prices == before.prices
        assert (after.last_cost, after.wac, after.status) == (
            before.last_cost,
            before.wac,
            ArticleStatus.ACTIVE,
        )
        assert (after.created_at, after.version) == (before.created_at, 1)


def test_brand_model_name_and_reference_unique_per_shop(
    backend: ContractBackend, shop_a: ShopId, shop_b: ShopId
) -> None:
    first = moto(shop_a)
    shirt = apparel(shop_a, "Chemise", "CH-0142")
    with backend.uow(shop_a) as uow:
        ArticleRepository.within(uow).add(first)
        ArticleRepository.within(uow).add(shirt)
        ArticleRepository.within(uow).add(moto(shop_a, model="HJ150"))  # sans référence : libre
        uow.commit()
    clashes = [
        (moto(shop_a, model="hj125 8", brand="HAOJUE"), ARTICLE_BRAND_MODEL),
        (apparel(shop_a, "Autre chemise", "ch 0142"), ARTICLE_REFERENCE),
        (apparel(shop_a, " CHÉMISE! ", "CH-9999"), ARTICLE_NAME),  # sans modèle : nom unique
    ]
    for article, constraint in clashes:
        with pytest.raises(Duplicate) as caught:
            run_in_uow(backend, shop_a, lambda uow, a=article: ArticleRepository.within(uow).add(a))  # type: ignore[misc]
        assert caught.value.details["constraint"] == constraint
    run_in_uow(backend, shop_b, lambda uow: ArticleRepository.within(uow).add(moto(shop_b)))
    same_name = apparel(shop_b, "Chemise", "CH-0142")  # autre boutique : libre
    run_in_uow(backend, shop_b, lambda uow: ArticleRepository.within(uow).add(same_name))
    with backend.uow(shop_a) as uow:
        articles = ArticleRepository.within(uow)
        found = articles.find_by_key(ARTICLE_BRAND_MODEL, first.details.brand_model_key or "")
        assert found is not None
        assert found.id == first.id
        assert articles.find_by_key(ARTICLE_REFERENCE, "ch 0142") is not None
        assert articles.find_by_key(ARTICLE_REFERENCE, "absent") is None
        named = articles.find_by_key(ARTICLE_NAME, "chemise")
        assert named is not None
        assert named.id == shirt.id
        assert first.details.name_key is None  # motos : marque + modèle


def test_isolation_between_shops(backend: ContractBackend, shop_a: ShopId, shop_b: ShopId) -> None:
    article = moto(shop_a)
    run_in_uow(backend, shop_a, lambda uow: ArticleRepository.within(uow).add(article))
    with backend.uow(shop_b) as uow:
        articles = ArticleRepository.within(uow)
        with pytest.raises(NotFound):
            articles.get(article.id)
        assert articles.find(article.id) is None
        assert articles.search(ArticleQuery(), ArticlePageRequest()).items == []
        with pytest.raises(IsolationViolation):
            articles.add(moto(shop_a, model="X"))


def test_optimistic_lock(backend: ContractBackend, shop_a: ShopId) -> None:
    article = moto(shop_a)
    run_in_uow(backend, shop_a, lambda uow: ArticleRepository.within(uow).add(article))
    with backend.uow(shop_a) as uow:
        mine = ArticleRepository.within(uow).get(article.id)
    with backend.uow(shop_a) as uow:
        stale = ArticleRepository.within(uow).get(article.id)
    mine.record_costs(last_cost=None, wac=None)
    run_in_uow(backend, shop_a, lambda uow: ArticleRepository.within(uow).update(mine))
    with pytest.raises(VersionConflict):
        run_in_uow(backend, shop_a, lambda uow: ArticleRepository.within(uow).update(stale))
    assert read_version(backend, shop_a, article) == 2


def read_version(backend: ContractBackend, shop_id: ShopId, article: Article) -> int:
    with backend.uow(shop_id) as uow:
        return ArticleRepository.within(uow).get(article.id).version


def test_search_filters_orders_and_pages(backend: ContractBackend, shop_a: ShopId) -> None:
    models = ["HJ125-8", "DK150", "Éclair", "Boxer"]
    articles = [moto(shop_a, model=model) for model in models]
    with backend.uow(shop_a) as uow:
        for article in articles:
            ArticleRepository.within(uow).add(article)
        uow.commit()
    archived = articles[3]
    with backend.uow(shop_a) as uow:
        repository = ArticleRepository.within(uow)
        stored = repository.get(archived.id)
        stored.status = ArticleStatus.ARCHIVED
        repository.update(stored)
        uow.commit()
    with backend.uow(shop_a) as uow:
        repository = ArticleRepository.within(uow)

        def names(query: ArticleQuery, page: ArticlePageRequest | None = None) -> list[str]:
            found = repository.search(query, page or ArticlePageRequest())
            return [a.details.fields.model or "" for a in found.items]

        assert names(ArticleQuery()) == ["DK150", "Éclair", "HJ125-8"]
        assert names(ArticleQuery("ECL")) == ["Éclair"]
        assert names(ArticleQuery("hj125 8")) == ["HJ125-8"]
        assert names(ArticleQuery(status=ArticleStatus.ARCHIVED)) == ["Boxer"]
        assert names(ArticleQuery(status=None)) == ["Boxer", "DK150", "Éclair", "HJ125-8"]
        first = repository.search(ArticleQuery(status=None), ArticlePageRequest(3))
        assert first.next_cursor is not None
        assert names(ArticleQuery(status=None), ArticlePageRequest(3, first.next_cursor)) == [
            "HJ125-8"
        ]


def test_price_history_append_only(
    backend: ContractBackend, shop_a: ShopId, shop_b: ShopId
) -> None:
    article, other = moto(shop_a), moto(shop_a, model="DK150")
    entries = [history(article, 0, 780_000), history(article, 5, 800_000), history(other, 1, 1)]
    with backend.uow(shop_a) as uow:
        log = PriceHistoryLog.within(uow)
        for entry in entries:
            log.append(entry)
        uow.commit()
    with backend.uow(shop_a) as uow:
        read = PriceHistoryLog.within(uow).for_article(article.id)
    assert read == [entries[1], entries[0]]
    assert not hasattr(PriceHistoryLog, "update")
    with backend.uow(shop_b) as uow:
        assert PriceHistoryLog.within(uow).for_article(article.id) == []
        with pytest.raises(IsolationViolation):
            PriceHistoryLog.within(uow).append(history(article, 9, 1))
    with pytest.raises(Duplicate):
        run_in_uow(backend, shop_a, lambda uow: PriceHistoryLog.within(uow).append(entries[0]))
