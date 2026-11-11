"""Les migrations Alembic produisent exactement le schéma déclaré (`tables.metadata`)."""

import sqlalchemy as sa
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.infrastructure.persistence.sqlalchemy.tables import metadata


def schema_drift(engine: sa.Engine) -> list[object]:
    """Différences entre la base migrée et `metadata` (tables du banc de tests ignorées)."""

    def production_only(name: str | None, type_: str, parent_names: object) -> bool:
        return type_ != "table" or name in metadata.tables

    with engine.connect() as connection:
        context = MigrationContext.configure(
            connection, opts={"include_name": production_only, "compare_type": True}
        )
        return list(compare_metadata(context, metadata))


def constraint_drift(engine: sa.Engine) -> dict[str, tuple[set[str], set[str]]]:
    """Noms de clé primaire et de `CHECK` : (déclarés, en base), pour chaque table qui diffère.

    `compare_metadata` ne compare pas les `CHECK` : les noms sont donc vérifiés ici (ils
    apparaissent dans les erreurs et doivent rester identiques sur toute base).
    """
    inspector = sa.inspect(engine)
    drift: dict[str, tuple[set[str], set[str]]] = {}
    for name, table in metadata.tables.items():
        declared = {str(c.name) for c in table.constraints if isinstance(c, sa.CheckConstraint)}
        declared.add(str(table.primary_key.name))
        actual = {str(c["name"]) for c in inspector.get_check_constraints(name)}
        actual.add(str(inspector.get_pk_constraint(name)["name"]))
        if declared != actual:
            drift[name] = (declared, actual)
    return drift


def test_migrations_match_declared_tables(sqlite_db: sa.Engine) -> None:
    assert schema_drift(sqlite_db) == []
    assert constraint_drift(sqlite_db) == {}
