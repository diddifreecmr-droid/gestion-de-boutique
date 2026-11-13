"""Migration `0015_mandatory_modules` (specs § 15.1) : une boutique réglée sans `catalog` ou
`sales` les retrouve ; les autres modules ne bougent pas ; une boutique complète est intacte ;
rejouer la migration ne change rien (idempotente)."""

import importlib.util
from pathlib import Path
from types import ModuleType
from uuid import uuid4

import sqlalchemy as sa
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext

from app.infrastructure.persistence.sqlalchemy.tables_shops import shop as shop_table
from tests.contracts.backends.postgres import PostgresContractBackend

MIGRATION = Path(__file__).parents[3] / "alembic" / "versions" / "0015_mandatory_modules.py"


def _migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("mandatory_modules", MIGRATION)
    if spec is None or spec.loader is None:
        msg = f"Migration illisible : {MIGRATION}"
        raise RuntimeError(msg)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _insert(connection: sa.Connection, modules: list[str]) -> object:
    shop_id = uuid4()
    connection.execute(
        shop_table.insert().values(
            id=shop_id, shop_id=shop_id, version=1, account_id=uuid4(), name=f"B {shop_id}",
            profile_code="motos", city="Garoua", phone="+237222000000",
            enabled_modules=modules, status="active", created_at=sa.func.now(),
        )
    )  # fmt: skip
    return shop_id


def _upgrade(connection: sa.Connection) -> None:
    with Operations.context(MigrationContext.configure(connection)):
        _migration().upgrade()


def test_upgrade_restores_catalog_and_sales_only(pg: PostgresContractBackend) -> None:
    with pg.engine.begin() as connection:
        old = _insert(connection, ["audit", "core", "expenses"])
        full = _insert(connection, ["audit", "catalog", "core", "sales", "transfers"])
        _upgrade(connection)
        _upgrade(connection)  # idempotente
        found = connection.execute(sa.select(shop_table.c.id, shop_table.c.enabled_modules))
        rows = {row.id: row.enabled_modules for row in found}
    assert rows[old] == ["audit", "catalog", "core", "expenses", "sales"]
    assert rows[full] == ["audit", "catalog", "core", "sales", "transfers"]
