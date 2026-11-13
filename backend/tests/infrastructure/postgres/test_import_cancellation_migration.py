"""Migration `0020_import_cancellation` (T35, QC-6) sur PostgreSQL : le téléphone d'un client
existant est recopié dans `phone_key` (unicité `customer_phone` déplacée), `article.keys_released`
faux, `supplier.name_key` nullable, table `import_problem` ; retour arrière puis remontée ; retour
arrière **refusé** dès qu'un élément a été retiré (clé libérée)."""

import importlib.util
from pathlib import Path
from types import ModuleType
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext

from tests.contracts.backends.postgres import PostgresContractBackend

MIGRATION = Path(__file__).parents[3] / "alembic" / "versions" / "0020_import_cancellation.py"


def _migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("import_cancellation", MIGRATION)
    if spec is None or spec.loader is None:
        msg = f"Migration illisible : {MIGRATION}"
        raise RuntimeError(msg)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _columns(connection: sa.Connection, table: str) -> dict[str, dict[str, object]]:
    return {c["name"]: dict(c) for c in sa.inspect(connection).get_columns(table)}


def _uniques(connection: sa.Connection) -> dict[str, list[str]]:
    found = sa.inspect(connection).get_unique_constraints("customer")
    return {str(u["name"]): list(u["column_names"]) for u in found}


def _old_customer(connection: sa.Connection) -> object:
    customer_id = uuid4()
    connection.execute(
        sa.text(
            "INSERT INTO customer (id, shop_id, version, name, phone, kind, search_key, sort_key,"
            " created_by, created_at) VALUES (:id, :shop, 1, 'Ali', '+237690000001',"
            " 'individual', 'ali', 'ali', :by, now())"
        ),
        {"id": customer_id, "shop": uuid4(), "by": uuid4()},
    )
    return customer_id


def test_downgrade_then_upgrade_keeps_phones(pg: PostgresContractBackend) -> None:
    migration = _migration()
    assert (migration.revision, migration.down_revision) == (
        "0020_import_cancellation", "0019_import_batches",
    )  # fmt: skip
    with (
        pg.engine.begin() as connection,
        Operations.context(MigrationContext.configure(connection)),
    ):
        assert "phone_key" in _columns(connection, "customer")  # base de test déjà à la tête
        migration.downgrade()
        assert "phone_key" not in _columns(connection, "customer")
        assert _uniques(connection)["customer_phone"] == ["shop_id", "phone"]
        assert not sa.inspect(connection).has_table("import_problem")
        customer_id = _old_customer(connection)
        migration.upgrade()
        copied = connection.execute(
            sa.text("SELECT phone_key FROM customer WHERE id = :id"), {"id": customer_id}
        ).scalar_one()
        uniques = _uniques(connection)
        released = _columns(connection, "article")["keys_released"]
        name_key = _columns(connection, "supplier")["name_key"]
        problems = sa.inspect(connection).has_table("import_problem")
        connection.execute(sa.text("DELETE FROM customer WHERE id = :id"), {"id": customer_id})
    assert copied == "+237690000001"
    assert uniques["customer_phone"] == ["shop_id", "phone_key"]
    assert (released["nullable"], name_key["nullable"], problems) == (False, True, True)


def test_downgrade_is_refused_once_a_key_was_freed(pg: PostgresContractBackend) -> None:
    migration = _migration()
    with (
        pytest.raises(RuntimeError, match="Retour arrière de 0020 impossible"),
        pg.engine.begin() as connection,
        Operations.context(MigrationContext.configure(connection)),
    ):
        connection.execute(
            sa.text(
                "INSERT INTO supplier (id, shop_id, version, name, name_key, active, created_at)"
                " VALUES (:id, :shop, 1, 'Ets Haojue', NULL, false, now())"
            ),
            {"id": uuid4(), "shop": uuid4()},
        )
        migration.downgrade()  # l'exception annule la transaction : rien ne reste
    with pg.engine.connect() as connection:
        assert "phone_key" in _columns(connection, "customer")
