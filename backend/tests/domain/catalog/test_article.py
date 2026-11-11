"""Agrégat `Article` : détails, prix, archivage, coûts réservés (UC-STK-01 à 04)."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.domain.audit.values import Performer
from app.domain.catalog.article import Article, with_reference
from app.domain.catalog.details import ArticleDetails, ArticleStatus
from app.domain.catalog.errors import MinPriceAboveBase, MinPriceDisabled, PiecePriceNotAllowed
from app.domain.catalog.events import ArticleChanged, ArticleCreated, ArticlePricesSet
from app.domain.catalog.ids import ArticleId, AttachmentId
from app.domain.catalog.prices import ArticlePrices, PriceHistory, PriceKind
from app.domain.catalog.schema import read_profile_fields
from app.domain.profiles.apparel import APPAREL, TEXTILE
from app.domain.profiles.motos import MOTOS
from app.domain.shared.errors import InvalidAmount, InvalidQuantity, InvalidStateTransition
from app.domain.shared.ids import ShopId, UserId
from app.domain.shared.money import Money

NOW = datetime(2026, 11, 11, 9, 0, tzinfo=UTC)
WHO = Performer(UserId.new(), "owner")


def moto(model: str = "HJ125-8", **extra: object) -> ArticleDetails:
    fields = read_profile_fields(MOTOS, {"brand": "Haojue", "model": model})
    return ArticleDetails(fields=fields, **extra)  # type: ignore[arg-type]


def created(details: ArticleDetails | None = None) -> Article:
    return Article.create(ShopId.new(), details or moto(), performer=WHO, now=NOW)


def test_create_records_event_and_keys() -> None:
    article = created()
    [event] = article.events.pull()
    assert isinstance(event, ArticleCreated)
    record = event.audit_record()
    assert (record.module, record.entity.number) == ("catalog", "Haojue HJ125-8")
    assert article.details.brand_model_key == "haojue|hj125 8"
    assert article.details.reference_key is None
    assert article.status is ArticleStatus.ACTIVE


def test_change_logs_before_after_and_reason() -> None:
    article = created()
    article.events.pull()
    renamed = moto("HJ125-8A", notes="Nouvelle série", alert_threshold=Decimal(3))
    assert article.change(renamed, performer=WHO, now=NOW, reason="Erreur de saisie")
    [event] = article.events.pull()
    assert isinstance(event, ArticleChanged)
    record = event.audit_record()
    changes = {c.field: (c.before, c.after) for c in record.changes}
    assert changes["display_name"] == ("Haojue HJ125-8", "Haojue HJ125-8A")
    assert changes["alert_threshold"] == (None, "3")
    assert record.reason == "Erreur de saisie"
    assert not article.change(renamed, performer=WHO, now=NOW)


def test_details_validation() -> None:
    with pytest.raises(InvalidQuantity):
        moto(alert_threshold=Decimal("2.5"))  # moto : seuil entier
    with pytest.raises(InvalidQuantity):
        moto(alert_threshold=Decimal(-1))
    with pytest.raises(TypeError):
        moto(photo_id="photo")
    photo = AttachmentId.new()
    details = moto(photo_id=photo, notes="  ")
    assert (details.photo_id, details.notes) == (photo, None)
    assert details.effective_threshold(Decimal(2)) == Decimal(2)
    assert moto(alert_threshold=Decimal(5)).effective_threshold(Decimal(2)) == Decimal(5)
    apparel = read_profile_fields(APPAREL, {"name": "Robe", "category": "Femme"})
    values = ArticleDetails(fields=apparel).profile_values(APPAREL)
    assert values["name"] == "Robe"
    assert values["category"] == "Femme"
    referenced = with_reference(ArticleDetails(fields=apparel), "REF-000001")
    assert referenced.reference_key == "ref 000001"


def test_prices_rules_and_history() -> None:
    article = created()
    with pytest.raises(MinPriceAboveBase):
        ArticlePrices(base_price=Money(700_000), min_price=Money(720_000))
    with pytest.raises(InvalidAmount):
        ArticlePrices(base_price=Money(-1))
    with pytest.raises(MinPriceDisabled):
        article.set_prices(
            ArticlePrices(min_price=Money(1)), min_price_enabled=False, performer=WHO, now=NOW
        )
    with pytest.raises(PiecePriceNotAllowed):
        article.set_prices(
            ArticlePrices(base_price_piece=Money(1)), min_price_enabled=True, performer=WHO, now=NOW
        )
    prices = ArticlePrices(base_price=Money(780_000), min_price=Money(720_000))
    article.events.pull()
    changes = article.set_prices(prices, min_price_enabled=True, performer=WHO, now=NOW)
    assert [(c.kind, c.old, c.new) for c in changes] == [
        (PriceKind.BASE, None, Money(780_000)),
        (PriceKind.MINIMUM, None, Money(720_000)),
    ]
    [event] = article.events.pull()
    assert isinstance(event, ArticlePricesSet)
    assert event.audit_record().sensitive
    assert prices.active_minimum(PriceKind.MINIMUM, min_price_enabled=False) is None
    assert prices.active_minimum(PriceKind.MINIMUM, min_price_enabled=True) == Money(720_000)
    with pytest.raises(ValueError, match="minimum"):
        prices.active_minimum(PriceKind.BASE, min_price_enabled=True)
    kept = ArticlePrices(base_price=Money(800_000), min_price=Money(720_000))
    [change] = article.set_prices(kept, min_price_enabled=False, performer=WHO, now=NOW)
    assert change.kind is PriceKind.BASE  # minimum inchangé : admis réglage désactivé
    assert article.set_prices(kept, min_price_enabled=False, performer=WHO, now=NOW) == []
    entry = PriceHistory.record(article.shop_id, article.id, change, author_id=WHO.user_id, at=NOW)
    assert (entry.old_price, entry.new_price) == (Money(780_000), Money(800_000))
    with pytest.raises(TypeError):
        PriceHistory.record(article.shop_id, ArticleId.new(), change, author_id=WHO, at=NOW)  # type: ignore[arg-type]


def test_piece_prices_follow_sold_by_piece() -> None:
    wax = read_profile_fields(
        TEXTILE, {"name": "Wax", "unit": "METER", "sold_by_piece": True, "piece_length_m": "6"}
    )
    article = created(ArticleDetails(fields=wax))
    prices = ArticlePrices(base_price=Money(2500), base_price_piece=Money(13_000))
    article.set_prices(prices, min_price_enabled=False, performer=WHO, now=NOW)
    by_meter = read_profile_fields(TEXTILE, {"name": "Wax", "unit": "METER"})
    with pytest.raises(PiecePriceNotAllowed):
        article.change(ArticleDetails(fields=by_meter), performer=WHO, now=NOW)


def test_archive_reactivate_and_costs() -> None:
    article = created()
    article.archive(performer=WHO, now=NOW)
    assert not article.is_active
    with pytest.raises(InvalidStateTransition):
        article.archive(performer=WHO, now=NOW)
    article.reactivate(performer=WHO, now=NOW)
    with pytest.raises(InvalidStateTransition):
        article.reactivate(performer=WHO, now=NOW)
    article.record_costs(last_cost=Money(600_000), wac=Money(590_000))
    assert (article.last_cost, article.wac) == (Money(600_000), Money(590_000))
    with pytest.raises(InvalidAmount):
        article.record_costs(last_cost=Money(-1), wac=None)
