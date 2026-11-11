"""Base de données en mémoire : l'**état validé**, partagé par toutes les unités de travail.

Comme une vraie base, elle survit aux transactions et n'expose que ce qui a été validé. Les
écritures d'une transaction arrivent ici en bloc par `apply`, qui revalide sous verrou tout ce
qu'une transaction concurrente aurait pu invalider (version, identifiant, unicité, séquence) :
tout est appliqué, ou rien.
"""

import threading
from collections.abc import Hashable, Mapping
from dataclasses import dataclass, field

from app.domain.shared.doc_number import DocType
from app.domain.shared.ids import EntityId, ShopId
from app.infrastructure.persistence.errors import PRIMARY_KEY
from app.infrastructure.persistence.errors import duplicate as duplicate  # réexport (compat.)
from app.infrastructure.persistence.errors import version_conflict as version_conflict

SequenceKey = tuple[ShopId, DocType]


@dataclass(frozen=True, slots=True)
class Row:
    """Ligne stockée : copie figée de l'agrégat (`payload`) et métadonnées d'indexation."""

    shop_id: ShopId
    entity_id: EntityId
    version: int
    unique: Mapping[str, Hashable]  # contraintes renseignées uniquement (les `None` sont omis)
    payload: object


@dataclass(frozen=True, slots=True)
class Write:
    """Écriture en attente : `expected_version` vaut `None` pour une insertion."""

    table: str
    row: Row
    expected_version: int | None


@dataclass(slots=True)
class ChangeSet:
    """Tout ce qu'une transaction veut valider."""

    writes: list[Write] = field(default_factory=list)
    sequences: dict[SequenceKey, tuple[int, int]] = field(default_factory=dict)  # (lu, nouveau)


def find_unique_clash(rows: Mapping[EntityId, Row], row: Row) -> str | None:
    """Nom de la première contrainte que `row` viole parmi `rows` (même boutique), ou `None`."""
    for other in rows.values():
        if other.entity_id == row.entity_id or other.shop_id != row.shop_id:
            continue
        for name, value in row.unique.items():
            if other.unique.get(name) == value:
                return name
    return None


class MemoryDatabase:
    """Tables `nom → {id → Row}` et compteurs de numérotation `(boutique, type) → dernier`."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._tables: dict[str, dict[EntityId, Row]] = {}
        self._sequences: dict[SequenceKey, int] = {}

    def read(self, table: str, entity_id: EntityId) -> Row | None:
        with self._lock:
            return self._tables.get(table, {}).get(entity_id)

    def rows(self, table: str, shop_id: ShopId) -> dict[EntityId, Row]:
        with self._lock:
            rows = self._tables.get(table, {})
            return {key: row for key, row in rows.items() if row.shop_id == shop_id}

    def sequence(self, key: SequenceKey) -> int:
        with self._lock:
            return self._sequences.get(key, 0)

    def apply(self, changes: ChangeSet) -> None:
        """Valide puis applique `changes` d'un bloc ; lève sans rien écrire en cas de conflit."""
        with self._lock:
            staged = {name: dict(rows) for name, rows in self._tables.items()}
            for write in changes.writes:
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
            for write in changes.writes:
                clash = find_unique_clash(staged[write.table], write.row)
                if clash is not None:
                    raise duplicate(write.table, clash)
            for key, (read, _) in changes.sequences.items():
                if self._sequences.get(key, 0) != read:
                    raise version_conflict(read, self._sequences.get(key, 0))
            self._tables = staged
            for key, (_, new) in changes.sequences.items():
                self._sequences[key] = new
