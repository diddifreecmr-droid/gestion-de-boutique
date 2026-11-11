"""Stockage mémoire de **portée plateforme** (identité) et sa transaction.

Pendant de `MemoryDatabase` / `MemoryTransaction`, sans `shop_id` : les lignes sont globales et
l'unicité (téléphone) vaut sur toute la plateforme. Mêmes garanties : écritures privées jusqu'au
commit (lecture validée), contrôles immédiats puis revalidés sous verrou au commit, tout ou rien.
Les tables de boutique (`MemoryDatabase`) ne sont jamais touchées.
"""

import threading
from collections.abc import Hashable, Mapping
from dataclasses import dataclass

from app.application.ports.errors import UnitOfWorkStateError
from app.application.ports.repository import not_found
from app.domain.shared.ids import EntityId
from app.infrastructure.persistence.errors import PRIMARY_KEY, duplicate, version_conflict


@dataclass(frozen=True, slots=True)
class PlatformRow:
    entity_id: EntityId
    version: int
    unique: Mapping[str, Hashable]
    payload: object


@dataclass(frozen=True, slots=True)
class PlatformWrite:
    table: str
    row: PlatformRow
    expected_version: int | None  # None : insertion


def unique_clash(rows: Mapping[EntityId, PlatformRow], row: PlatformRow) -> str | None:
    for other in rows.values():
        if other.entity_id == row.entity_id:
            continue
        for name, value in row.unique.items():
            if other.unique.get(name) == value:
                return name
    return None


class MemoryPlatformStore:
    """État validé des tables plateforme : `nom → {id → PlatformRow}`."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._tables: dict[str, dict[EntityId, PlatformRow]] = {}

    def rows(self, table: str) -> dict[EntityId, PlatformRow]:
        with self._lock:
            return dict(self._tables.get(table, {}))

    def apply(self, writes: list[PlatformWrite]) -> None:
        with self._lock:
            staged = {name: dict(rows) for name, rows in self._tables.items()}
            for write in writes:
                table = staged.setdefault(write.table, {})
                current = table.get(write.row.entity_id)
                if write.expected_version is None and current is not None:
                    raise duplicate(write.table, PRIMARY_KEY)
                if write.expected_version is not None and (
                    current is None or current.version != write.expected_version
                ):
                    raise version_conflict(
                        write.expected_version, None if current is None else current.version
                    )
                table[write.row.entity_id] = write.row
            for write in writes:
                clash = unique_clash(staged[write.table], write.row)
                if clash is not None:
                    raise duplicate(write.table, clash)
            self._tables = staged


class MemoryPlatformTransaction:
    """Jeu d'écritures privé d'une `IdentityUnitOfWork` mémoire."""

    def __init__(self, store: MemoryPlatformStore) -> None:
        self._store = store
        self._writes: dict[tuple[str, EntityId], PlatformWrite] = {}
        self._closed = False

    def visible(self, table: str) -> dict[EntityId, PlatformRow]:
        """Lignes validées, recouvertes par les écritures de cette transaction."""
        self._require_open()
        rows = self._store.rows(table)
        for (name, entity_id), write in self._writes.items():
            if name == table:
                rows[entity_id] = write.row
        return rows

    def insert(self, table: str, row: PlatformRow) -> None:
        rows = self.visible(table)
        if row.entity_id in rows:
            raise duplicate(table, PRIMARY_KEY)
        self._require_unique(table, rows, row)
        self._writes[(table, row.entity_id)] = PlatformWrite(table, row, expected_version=None)

    def update(self, table: str, row: PlatformRow, expected_version: int) -> None:
        rows = self.visible(table)
        current = rows.get(row.entity_id)
        if current is None:
            raise not_found(row.entity_id)
        if current.version != expected_version:
            raise version_conflict(expected_version, current.version)
        self._require_unique(table, rows, row)
        previous = self._writes.get((table, row.entity_id))
        base = expected_version if previous is None else previous.expected_version
        self._writes[(table, row.entity_id)] = PlatformWrite(table, row, expected_version=base)

    @property
    def has_changes(self) -> bool:
        return bool(self._writes)

    def commit(self) -> None:
        self._require_open()
        self._closed = True
        self._store.apply(list(self._writes.values()))

    def discard(self) -> None:
        self._closed = True
        self._writes.clear()

    @staticmethod
    def _require_unique(table: str, rows: Mapping[EntityId, PlatformRow], row: PlatformRow) -> None:
        clash = unique_clash(rows, row)
        if clash is not None:
            raise duplicate(table, clash)

    def _require_open(self) -> None:
        if self._closed:
            msg = "Transaction mémoire plateforme déjà validée ou annulée"
            raise UnitOfWorkStateError(msg)
