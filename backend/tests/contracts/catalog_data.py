"""Données de contrat du catalogue : articles construits par le domaine (ports seulement)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.domain.catalog.article import Article
from app.domain.catalog.details import ArticleDetails
from app.domain.catalog.ids import ArticleId, AttachmentId
from app.domain.catalog.prices import ArticlePrices, PriceChange, PriceHistory, PriceKind
from app.domain.catalog.schema import read_profile_fields
from app.domain.profiles.apparel import APPAREL, TEXTILE
from app.domain.profiles.motos import MOTOS
from app.domain.shared.ids import ShopId, UserId
from app.domain.shared.money import Money

NOW = datetime(2026, 11, 11, 9, 0, tzinfo=UTC)


def moto(shop_id: ShopId, model: str = "HJ125-8", brand: str = "Haojue") -> Article:
    fields = read_profile_fields(
        MOTOS, {"brand": brand, "model": model, "engine_cc": 125, "category": "Route"}
    )
    return Article(
        id=ArticleId.new(),
        shop_id=shop_id,
        details=ArticleDetails(fields=fields, alert_threshold=Decimal(5), notes="Série 2026"),
        created_at=NOW,
        prices=ArticlePrices(base_price=Money(780_000), min_price=Money(720_000)),
    )


def apparel(shop_id: ShopId, name: str, reference: str) -> Article:
    fields = read_profile_fields(APPAREL, {"name": name, "reference": reference})
    return Article(
        id=ArticleId.new(), shop_id=shop_id, details=ArticleDetails(fields=fields), created_at=NOW
    )


def wax(shop_id: ShopId) -> Article:
    fields = read_profile_fields(
        TEXTILE,
        {"name": "Wax Fleur", "unit": "METER", "sold_by_piece": True, "piece_length_m": "5.49"},
    )
    details = ArticleDetails(
        fields=fields, alert_threshold=Decimal("20.5"), photo_id=AttachmentId.new()
    )
    article = Article(
        id=ArticleId.new(),
        shop_id=shop_id,
        details=details,
        created_at=NOW,
        prices=ArticlePrices(base_price=Money(2_500), base_price_piece=Money(13_000)),
    )
    article.record_costs(last_cost=Money(1_800), wac=Money(1_750))
    return article


def history(article: Article, minutes: int, new: int) -> PriceHistory:
    change = PriceChange(PriceKind.BASE, None, Money(new))
    return PriceHistory.record(
        article.shop_id,
        article.id,
        change,
        author_id=UserId.new(),
        at=NOW + timedelta(minutes=minutes),
    )
