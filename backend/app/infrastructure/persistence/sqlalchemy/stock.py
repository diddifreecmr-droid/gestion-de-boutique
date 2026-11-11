"""Adaptateurs SQL du stock (T14, 1/2) : projection `stock_level` et grand livre `stock_movement`.

La projection suit le gabarit `SqlRepository` : `UPDATE … WHERE version = :lue`. Sur
PostgreSQL, la seconde de deux sorties simultanées **attend** le verrou de ligne de la première
puis ne trouve plus la version lue : `VersionConflict` (rejouée par `with_stock_retry`).
"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

import sqlalchemy as sa

from app.application.ports.pagination import Page, PageRequest, page_of
from app.application.stock.ports import StockLevelRepository, StockMovementLog, movement_position
from app.domain.catalog.ids import ArticleId
from app.domain.shared.ids import ShopId, UserId
from app.domain.shared.money import Money
from app.domain.shared.quantity import Quantity, StockUnit
from app.domain.shops.ids import LocationId
from app.domain.stock.ids import StockLevelId, StockMovementId
from app.domain.stock.level import StockLevel
from app.domain.stock.movement import StockMovement
from app.domain.stock.values import MovementType, SourceRef, SourceType, StockCondition
from app.infrastructure.persistence.errors import PRIMARY_KEY, duplicate
from app.infrastructure.persistence.sqlalchemy import tables_stock as t
from app.infrastructure.persistence.sqlalchemy.columns import before_cursor, from_db, to_db
from app.infrastructure.persistence.sqlalchemy.shop_store import SqlShopStore
from app.infrastructure.persistence.sqlalchemy.shops import SqlListing


def quantity(value: object, unit: StockUnit) -> Quantity:
    return Quantity.of(Decimal(str(value)), unit)


def optional_quantity(value: object, unit: StockUnit) -> Quantity | None:
    return None if value is None else quantity(value, unit)


class SqlStockLevelRepository(SqlListing[StockLevelId, StockLevel], StockLevelRepository):
    table = t.stock_level

    def _to_columns(self, aggregate: StockLevel) -> dict[str, Any]:
        return {
            "article_id": aggregate.article_id.value,
            "location_id": aggregate.location_id.value,
            "unit": aggregate.unit.value,
            "sellable": aggregate.sellable.value,
            "damaged": aggregate.damaged.value,
            "incoming": aggregate.incoming.value,
        }

    def _from_row(self, row: sa.RowMapping) -> StockLevel:
        unit = StockUnit(row["unit"])
        return StockLevel(
            id=StockLevelId(row["id"]),
            shop_id=ShopId(row["shop_id"]),
            article_id=ArticleId(row["article_id"]),
            location_id=LocationId(row["location_id"]),
            sellable=quantity(row["sellable"], unit),
            damaged=quantity(row["damaged"], unit),
            incoming=quantity(row["incoming"], unit),
            version=int(row["version"]),
        )

    def find_level(self, article_id: ArticleId, location_id: LocationId) -> StockLevel | None:
        c = self.table.c
        where = sa.and_(c.article_id == article_id.value, c.location_id == location_id.value)
        found = self._select_all(c.id, where=where)
        return found[0] if found else None

    def for_article(self, article_id: ArticleId) -> list[StockLevel]:
        return self._select_all(self.table.c.id, where=self.table.c.article_id == article_id.value)

    def for_location(self, location_id: LocationId) -> list[StockLevel]:
        c = self.table.c
        return self._select_all(c.id, where=c.location_id == location_id.value)

    def list_all(self) -> list[StockLevel]:
        return self._select_all(self.table.c.id)


class SqlStockMovementLog(SqlShopStore, StockMovementLog):
    table = t.stock_movement

    def _append(self, movement: StockMovement) -> None:
        values = {
            "id": movement.id.value,
            "shop_id": movement.shop_id.value,
            "article_id": movement.article_id.value,
            "location_id": movement.location_id.value,
            "type": movement.type.value,
            "condition": movement.condition.value,
            "unit": movement.quantity.unit.value,
            "quantity": movement.quantity.value,
            "balance_after": movement.balance_after.value,
            "source_type": movement.source.type.value,
            "source_id": movement.source.id,
            "source_number": movement.source.number,
            "unit_cost": None if movement.unit_cost is None else movement.unit_cost.amount,
            "occurred_at": to_db(movement.occurred_at),
            "recorded_at": to_db(movement.recorded_at),
            "author_id": movement.author_id.value,
            "stock_to_verify": movement.stock_to_verify,
            "reverses_id": None if movement.reverses is None else movement.reverses.value,
        }
        try:
            self._transaction.write(sa.insert(self.table).values(values))
        except sa.exc.IntegrityError as exc:
            taken = sa.select(self.table.c.id).where(self.table.c.id == movement.id.value)
            if not self._transaction.exists(taken):
                raise  # autre contrainte (double annulation…) : l'erreur remonte (fail-fast)
            raise duplicate(self.table.name, PRIMARY_KEY) from exc

    def _select(self, *conditions: sa.ColumnElement[bool]) -> sa.Select[Any]:
        c = self.table.c
        return sa.select(self.table).where(self._own_shop(), *conditions).order_by(c.id)

    def _fetch(self, statement: sa.Select[Any]) -> list[StockMovement]:
        return [movement_from_row(row) for row in self._transaction.fetch_all(statement)]

    def find(self, movement_id: StockMovementId) -> StockMovement | None:
        found = self._fetch(self._select(self.table.c.id == movement_id.value))
        return found[0] if found else None

    def reversal_of(self, movement_id: StockMovementId) -> StockMovement | None:
        found = self._fetch(self._select(self.table.c.reverses_id == movement_id.value))
        return found[0] if found else None

    def for_source(self, source_id: UUID) -> list[StockMovement]:
        return self._fetch(self._select(self.table.c.source_id == source_id))

    def for_article(self, article_id: ArticleId, page: PageRequest) -> Page[StockMovement]:
        c = self.table.c
        conditions = [self._own_shop(), c.article_id == article_id.value]
        if page.after is not None:
            conditions.append(before_cursor(c.occurred_at, c.id, page.after))
        statement = (
            sa.select(self.table)
            .where(*conditions)
            .order_by(c.occurred_at.desc(), c.id.desc())
            .limit(page.limit + 1)
        )
        return page_of(self._fetch(statement), page, movement_position)

    def count_sources_since(
        self, location_id: LocationId, movement_type: MovementType, since: datetime
    ) -> int:
        c = self.table.c
        statement = sa.select(sa.func.count(sa.distinct(c.source_id))).where(
            self._own_shop(),
            c.location_id == location_id.value,
            c.type == movement_type.value,
            c.recorded_at >= to_db(since),
        )
        row = self._transaction.fetch_one(statement)
        return 0 if row is None else int(next(iter(row.values())))


def movement_from_row(row: sa.RowMapping) -> StockMovement:
    unit = StockUnit(row["unit"])
    cost, reverses = row["unit_cost"], row["reverses_id"]
    return StockMovement(
        id=StockMovementId(row["id"]),
        shop_id=ShopId(row["shop_id"]),
        article_id=ArticleId(row["article_id"]),
        location_id=LocationId(row["location_id"]),
        type=MovementType(row["type"]),
        condition=StockCondition(row["condition"]),
        quantity=quantity(row["quantity"], unit),
        balance_after=quantity(row["balance_after"], unit),
        source=SourceRef(SourceType(row["source_type"]), row["source_id"], row["source_number"]),
        occurred_at=from_db(row["occurred_at"]),
        recorded_at=from_db(row["recorded_at"]),
        author_id=UserId(row["author_id"]),
        unit_cost=None if cost is None else Money(int(cost)),
        stock_to_verify=bool(row["stock_to_verify"]),
        reverses=None if reverses is None else StockMovementId(reverses),
    )
