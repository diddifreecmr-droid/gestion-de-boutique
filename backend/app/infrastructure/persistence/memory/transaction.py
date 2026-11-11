"""Transaction en mémoire : jeu d'écritures privé, invisible des autres jusqu'au commit.

Isolation « lecture validée » (comme PostgreSQL par défaut) : une lecture voit les écritures
de la transaction elle-même, sinon l'état validé de la base. Les contrôles (identifiant pris,
unicité, version) sont faits **tout de suite** pour échouer au plus près de la cause, puis
refaits par `MemoryDatabase.apply` au commit contre les transactions concurrentes. Un rollback
jette simplement le jeu d'écritures : la base n'a jamais été touchée.
"""

from app.application.ports.errors import UnitOfWorkStateError
from app.application.ports.repository import not_found
from app.domain.shared.doc_number import DocType
from app.domain.shared.ids import EntityId, ShopId
from app.infrastructure.persistence.errors import PRIMARY_KEY, duplicate, version_conflict
from app.infrastructure.persistence.memory.database import (
    ChangeSet,
    MemoryDatabase,
    Row,
    SequenceKey,
    Write,
    find_unique_clash,
)


class MemoryTransaction:
    """Transaction d'une unité de travail mémoire, liée à une boutique."""

    def __init__(self, database: MemoryDatabase, shop_id: ShopId) -> None:
        self._database = database
        self._shop_id = shop_id
        self._writes: dict[tuple[str, EntityId], Write] = {}
        self._sequences: dict[SequenceKey, tuple[int, int]] = {}
        self._closed = False

    # ------------------------------------------------------------------ lecture
    def load(self, table: str, entity_id: EntityId) -> Row | None:
        """Ligne visible de la boutique, ou `None` (absente **ou** d'une autre boutique)."""
        self._require_open()
        write = self._writes.get((table, entity_id))
        row = write.row if write is not None else self._database.read(table, entity_id)
        if row is None or row.shop_id != self._shop_id:
            return None
        return row

    # ------------------------------------------------------------------ écriture
    def insert(self, table: str, row: Row) -> None:
        self._require_open()
        key = (table, row.entity_id)
        if key in self._writes or self._database.read(table, row.entity_id) is not None:
            raise duplicate(
                table, PRIMARY_KEY
            )  # identifiant global (clé primaire), toutes boutiques
        self._require_unique(table, row)
        self._writes[key] = Write(table, row, expected_version=None)

    def update(self, table: str, row: Row, expected_version: int) -> None:
        self._require_open()
        current = self.load(table, row.entity_id)
        if current is None:
            raise not_found(row.entity_id)
        if current.version != expected_version:
            raise version_conflict(expected_version, current.version)
        self._require_unique(table, row)
        key = (table, row.entity_id)
        previous = self._writes.get(key)
        # Version attendue par la base au commit : celle lue au premier contact (None si
        # l'agrégat a été inséré par cette même transaction).
        base = expected_version if previous is None else previous.expected_version
        self._writes[key] = Write(table, row, expected_version=base)

    def next_sequence(self, doc_type: DocType) -> int:
        self._require_open()
        key = (self._shop_id, doc_type)
        if key not in self._sequences:
            committed = self._database.sequence(key)  # valeur revérifiée au commit
            self._sequences[key] = (committed, committed)
        read, current = self._sequences[key]
        self._sequences[key] = (read, current + 1)
        return current + 1

    # ------------------------------------------------------------------ fin
    @property
    def has_changes(self) -> bool:
        return bool(self._writes or self._sequences)

    def commit(self) -> None:
        self._require_open()
        self._closed = True
        self._database.apply(
            ChangeSet(writes=list(self._writes.values()), sequences=dict(self._sequences))
        )

    def discard(self) -> None:
        """Rollback : le jeu d'écritures est jeté (la base n'a jamais été modifiée)."""
        self._closed = True
        self._writes.clear()
        self._sequences.clear()

    # ------------------------------------------------------------------ interne
    def _require_unique(self, table: str, row: Row) -> None:
        visible = self._database.rows(table, self._shop_id)
        for (name, entity_id), write in self._writes.items():
            if name == table:
                visible[entity_id] = write.row
        clash = find_unique_clash(visible, row)
        if clash is not None:
            raise duplicate(table, clash)

    def _require_open(self) -> None:
        if self._closed:
            msg = "Transaction mémoire déjà validée ou annulée"
            raise UnitOfWorkStateError(msg)
