"""Traduction portable des violations d'unicité SQL en `Duplicate` (erreur de port).

Les pilotes ne nomment pas tous la contrainte violée (SQLite ne donne que les colonnes) et le
format de leurs messages varie : plutôt que d'analyser un message propre à un moteur, on
**rejoue la question** après l'échec, dans la même transaction (le savepoint fautif est déjà
annulé) : l'identifiant est-il pris ? sinon, quelle `UniqueKey` déclarée a déjà cette valeur ?
Une `IntegrityError` qu'aucune de ces sondes n'explique (`CHECK`, clé étrangère…) n'est pas un
doublon : elle est relancée telle quelle (fail-fast).
"""

from collections.abc import Iterable, Mapping, Sequence

import sqlalchemy as sa

from app.domain.shared.errors import Duplicate
from app.infrastructure.persistence.errors import PRIMARY_KEY, duplicate
from app.infrastructure.persistence.sqlalchemy.transaction import SqlTransaction

UniqueColumns = Mapping[str, Sequence[sa.Column[object]]]


def unique_columns(table: sa.Table, names: Iterable[str]) -> dict[str, Sequence[sa.Column[object]]]:
    """Colonnes de chaque contrainte `UNIQUE` nommée ; `TypeError` si elle manque au schéma.

    Convention (specs § 5.1) : l'unicité métier vaut **dans une boutique**, la contrainte
    commence donc par `shop_id`.
    """
    declared: dict[str, Sequence[sa.Column[object]]] = {}
    for constraint in table.constraints:
        if isinstance(constraint, sa.UniqueConstraint) and isinstance(constraint.name, str):
            declared[constraint.name] = list(constraint.columns)
    for index in table.indexes:
        if index.unique and isinstance(index.name, str):
            declared[index.name] = [c for c in index.columns if isinstance(c, sa.Column)]
    found: dict[str, Sequence[sa.Column[object]]] = {}
    for name in names:
        columns = declared.get(name)
        if columns is None:
            msg = f"UniqueKey {name!r} sans contrainte UNIQUE de ce nom sur la table {table.name}"
            raise TypeError(msg)
        if columns[0].name != "shop_id":
            msg = f"La contrainte {name!r} de {table.name} doit commencer par shop_id"
            raise TypeError(msg)
        found[name] = columns
    return found


def identify_duplicate(
    transaction: SqlTransaction,
    table: sa.Table,
    values: Mapping[str, object],
    unique: UniqueColumns,
    *,
    is_insert: bool,
) -> Duplicate | None:
    """`Duplicate` qui explique l'échec d'écriture de `values`, ou `None` si aucun."""
    entity_id = values[PRIMARY_KEY]
    if is_insert and transaction.exists(sa.select(table.c.id).where(table.c.id == entity_id)):
        return duplicate(table.name, PRIMARY_KEY)  # identifiant global, toutes boutiques
    for name, columns in unique.items():
        if any(values[column.name] is None for column in columns):
            continue  # NULL : non contraint, comme `UniqueKey.extract` → None
        clash = sa.select(table.c.id).where(
            *(column == values[column.name] for column in columns), table.c.id != entity_id
        )
        if transaction.exists(clash):
            return duplicate(table.name, name)
    return None
