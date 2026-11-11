"""Gabarit de dépôt SQL : implémente les trois primitives du port `Repository`.

Un dépôt concret hérite de ce gabarit **et** de son port, nomme sa table et fournit la
correspondance agrégat ↔ colonnes :

    class SqlWidgetRepository(SqlRepository[WidgetId, Widget], WidgetRepository):
        table = widget_table          # colonnes id, shop_id, version + colonnes métier

        def _to_columns(self, widget): return {"label": widget.label, "code": widget.code}
        def _from_row(self, row): return Widget(WidgetId(row["id"]), ...)

Chaque `UniqueKey` du port doit exister au schéma sous le même nom (`UNIQUE (shop_id, …)`) :
c'est vérifié à la construction. Chaque requête filtre sur la boutique du dépôt (specs § 8.3).
"""

from abc import abstractmethod
from typing import Any, ClassVar

import sqlalchemy as sa

from app.application.ports.aggregate import Aggregate, AggregateTracker
from app.application.ports.repository import Repository, not_found
from app.domain.shared.ids import EntityId, ShopId
from app.infrastructure.persistence.errors import version_conflict
from app.infrastructure.persistence.sqlalchemy.constraints import (
    identify_duplicate,
    unique_columns,
)
from app.infrastructure.persistence.sqlalchemy.transaction import SqlTransaction, Write

IDENTITY_COLUMNS = ("id", "shop_id", "version")


class SqlRepository[IdT: EntityId, AggT: Aggregate](Repository[IdT, AggT]):
    """Dépôt SQL générique, lié à une boutique et à une transaction."""

    table: ClassVar[sa.Table]

    def __init__(
        self, shop_id: ShopId, tracker: AggregateTracker, transaction: SqlTransaction
    ) -> None:
        table = getattr(type(self), "table", None)
        if not isinstance(table, sa.Table):
            msg = f"{type(self).__name__} doit déclarer l'attribut de classe `table` (sa.Table)"
            raise TypeError(msg)
        missing = [name for name in IDENTITY_COLUMNS if name not in table.c]
        if missing:
            msg = f"Table {table.name} : colonnes obligatoires absentes {missing}"
            raise TypeError(msg)
        super().__init__(shop_id, tracker)
        self._transaction = transaction
        self._unique = unique_columns(table, [key.name for key in self.unique_keys()])

    # ------------------------------------------------------------------ correspondance
    @abstractmethod
    def _to_columns(self, aggregate: AggT) -> dict[str, Any]:
        """Colonnes métier de l'agrégat (sans `id`, `shop_id` ni `version`)."""

    @abstractmethod
    def _from_row(self, row: sa.RowMapping) -> AggT:
        """Agrégat neuf (sans événement) reconstruit depuis une ligne de `table`."""

    # ------------------------------------------------------------------ primitives
    def _load(self, entity_id: IdT) -> AggT | None:
        row = self._transaction.fetch_one(sa.select(self.table).where(self._own(entity_id)))
        return None if row is None else self._from_row(row)

    def _insert(self, aggregate: AggT) -> None:
        values = self._values(aggregate)
        self._write(sa.insert(self.table).values(values), values, is_insert=True)

    def _save(self, aggregate: AggT, *, expected_version: int) -> None:
        values = self._values(aggregate)
        changes = {k: v for k, v in values.items() if k not in ("id", "shop_id")}
        statement = (
            sa.update(self.table)
            .where(self._own(aggregate.id), self.table.c.version == expected_version)
            .values(changes)
        )
        if self._write(statement, values, is_insert=False) == 1:
            return
        current = self._transaction.fetch_one(
            sa.select(self.table.c.version).where(self._own(aggregate.id))
        )
        if current is None:
            raise not_found(aggregate.id)  # absent, ou d'une autre boutique : même erreur
        raise version_conflict(expected_version, int(current["version"]))

    # ------------------------------------------------------------------ interne
    def _own(self, entity_id: EntityId) -> sa.ColumnElement[bool]:
        """Filtre « cet identifiant, dans la boutique du dépôt » (jamais l'un sans l'autre)."""
        return sa.and_(
            self.table.c.id == entity_id.value, self.table.c.shop_id == self.shop_id.value
        )

    def _values(self, aggregate: AggT) -> dict[str, Any]:
        columns = self._to_columns(aggregate)
        clash = [name for name in IDENTITY_COLUMNS if name in columns]
        if clash:
            msg = f"{type(self).__name__}._to_columns ne doit pas fournir {clash}"
            raise ValueError(msg)
        identity = {
            "id": aggregate.id.value,
            "shop_id": aggregate.shop_id.value,
            "version": aggregate.version,
        }
        return identity | columns

    def _write(self, statement: Write, values: dict[str, Any], *, is_insert: bool) -> int:
        try:
            return self._transaction.write(statement)
        except sa.exc.IntegrityError as exc:
            found = identify_duplicate(
                self._transaction, self.table, values, self._unique, is_insert=is_insert
            )
            if found is None:
                raise  # CHECK, clé étrangère… : pas un doublon, l'erreur remonte telle quelle
            raise found from exc
