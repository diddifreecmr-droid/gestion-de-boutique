"""Données de contrat du stock : boutique, deux lieux, un article, construits par les ports."""

from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID, uuid4

from app.application.catalog.ports import ArticleRepository
from app.application.shops.ports import LocationRepository
from app.domain.catalog.article import Article
from app.domain.catalog.ids import ArticleId
from app.domain.shared.ids import ShopId, UserId
from app.domain.shared.money import Money
from app.domain.shared.quantity import Quantity, StockUnit
from app.domain.shops.ids import LocationId, MerchantAccountId
from app.domain.shops.location import Location
from app.domain.stock.ids import StockMovementId
from app.domain.stock.movement import StockMovement
from app.domain.stock.values import (
    Direction,
    MovementType,
    SourceRef,
    SourceType,
    StockCondition,
)
from tests.contracts.backends import ContractBackend
from tests.contracts.catalog_data import NOW, moto
from tests.contracts.shop_data import seed_shop_and_settings, store

AUTHOR = UserId.new()


@dataclass(frozen=True)
class Seeded:
    garoua: Location
    depot: Location
    article: Article


def seed(backend: ContractBackend, shop_id: ShopId) -> Seeded:
    with backend.uow(shop_id) as uow:
        garoua = seed_shop_and_settings(uow, MerchantAccountId.new())
        depot = store(shop_id, "Garoua-Boulaï")
        LocationRepository.within(uow).add(depot)
        article = moto(shop_id)
        ArticleRepository.within(uow).add(article)
        uow.commit()
    return Seeded(garoua, depot, article)


def units(value: int | str) -> Quantity:
    return Quantity.of(value, StockUnit.UNIT)


def movement(
    shop_id: ShopId,
    article_id: ArticleId,
    location_id: LocationId,
    *,
    kind: MovementType = MovementType.OPENING,
    quantity: int = 1,
    minutes: int = 0,
    source: UUID | None = None,
    reverses: StockMovementId | None = None,
) -> StockMovement:
    sign = {Direction.IN: 1, Direction.OUT: -1}.get(kind.direction)
    signed = quantity if sign is None else sign * abs(quantity)
    return StockMovement(
        id=StockMovementId.new(),
        shop_id=shop_id,
        article_id=article_id,
        location_id=location_id,
        type=kind,
        condition=StockCondition.SELLABLE,
        quantity=units(signed),
        balance_after=units(quantity),
        source=SourceRef(SourceType.IMPORT, source or uuid4(), "IMP-000001"),
        occurred_at=NOW + timedelta(minutes=minutes),
        recorded_at=NOW + timedelta(minutes=minutes),
        author_id=AUTHOR,
        unit_cost=Money(500_000) if kind is MovementType.OPENING else None,
        reverses=reverses,
    )
