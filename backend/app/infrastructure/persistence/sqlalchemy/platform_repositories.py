"""Gabarit SQL des dépôts **plateforme** (sans `shop_id`) : mêmes règles que `SqlRepository`.

Verrou optimiste par `UPDATE … WHERE version = :attendue` ; une violation d'unicité est
traduite en `Duplicate` en **rejouant la question** (identifiant pris ? valeur unique prise ?),
comme `constraints.py` ; toute autre `IntegrityError` remonte telle quelle (fail-fast).
"""

from abc import abstractmethod
from collections.abc import Mapping, Sequence
from typing import Any, ClassVar

import sqlalchemy as sa

from app.application.identity.repositories import (
    PlatformAggregate,
    PlatformRepository,
    PlatformTracker,
)
from app.application.ports.repository import not_found
from app.domain.shared.ids import EntityId
from app.infrastructure.persistence.errors import PRIMARY_KEY, duplicate, version_conflict
from app.infrastructure.persistence.sqlalchemy.transaction import SqlTransaction, Write


class SqlPlatformRepository[IdT: EntityId, AggT: PlatformAggregate](PlatformRepository[IdT, AggT]):
    table: ClassVar[sa.Table]
    unique: ClassVar[Mapping[str, str]] = {}
    """Nom de contrainte → colonne unique (une seule colonne, portée plateforme)."""

    def __init__(self, tracker: PlatformTracker, transaction: SqlTransaction) -> None:
        super().__init__(tracker)
        self._transaction = transaction

    @abstractmethod
    def _to_columns(self, aggregate: AggT) -> dict[str, Any]:
        """Colonnes métier (sans `id` ni `version`)."""

    @abstractmethod
    def _from_row(self, row: sa.RowMapping) -> AggT: ...

    def _select(
        self, *conditions: sa.ColumnElement[bool], order_by: Sequence[Any] = ()
    ) -> list[AggT]:
        statement = sa.select(self.table).where(*conditions).order_by(*order_by)
        rows = self._transaction.fetch_all(statement)
        return self._tracked([self._from_row(row) for row in rows])

    def _load(self, entity_id: IdT) -> AggT | None:
        row = self._transaction.fetch_one(
            sa.select(self.table).where(self.table.c.id == entity_id.value)
        )
        return None if row is None else self._from_row(row)

    def _insert(self, aggregate: AggT) -> None:
        values = self._values(aggregate)
        self._write(sa.insert(self.table).values(values), values, is_insert=True)

    def _save(self, aggregate: AggT, *, expected_version: int) -> None:
        values = self._values(aggregate)
        c = self.table.c
        statement = (
            sa.update(self.table)
            .where(c.id == aggregate.id.value, c.version == expected_version)
            .values({k: v for k, v in values.items() if k != "id"})
        )
        if self._write(statement, values, is_insert=False) == 1:
            return
        current = self._transaction.fetch_one(
            sa.select(c.version).where(c.id == aggregate.id.value)
        )
        if current is None:
            raise not_found(aggregate.id)
        raise version_conflict(expected_version, int(current["version"]))

    def _values(self, aggregate: AggT) -> dict[str, Any]:
        return {"id": aggregate.id.value, "version": aggregate.version} | self._to_columns(
            aggregate
        )

    def _write(self, statement: Write, values: dict[str, Any], *, is_insert: bool) -> int:
        try:
            return self._transaction.write(statement)
        except sa.exc.IntegrityError as exc:
            c = self.table.c
            if is_insert and self._transaction.exists(sa.select(c.id).where(c.id == values["id"])):
                raise duplicate(self.table.name, PRIMARY_KEY) from exc
            for constraint, column in self.unique.items():
                clash = sa.select(c.id).where(c[column] == values[column], c.id != values["id"])
                if self._transaction.exists(clash):
                    raise duplicate(self.table.name, constraint) from exc
            raise  # CHECK… : pas un doublon, l'erreur remonte telle quelle
