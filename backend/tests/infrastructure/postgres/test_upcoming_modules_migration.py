"""Migration `0017_upcoming_modules` (specs § 15.1, décision du 2026-11-13) : `transfers`,
`transport` et `import` sont retirés de chaque boutique ; les autres modules ne bougent pas ;
une boutique sans module à venir est intacte ; rejouer la migration ne change rien."""

import importlib.util
from pathlib import Path
from types import ModuleType
from uuid import uuid4

import sqlalchemy as sa
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext

from app.infrastructure.persistence.sqlalchemy.tables_shops import shop as shop_table
from tests.contracts.backends.postgres import PostgresContractBackend

MIGRATION = Path(__file__).parents[3] / "alembic" / "versions" / "0017_upcoming_modules.py"


def _migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("upcoming_modules", MIGRATION)
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


def test_upgrade_removes_upcoming_modules_only(pg: PostgresContractBackend) -> None:
    every = [
        "audit", "catalog", "core", "dashboard", "expenses", "import", "purchases",
        "receivables", "sales", "transfers", "transport",
    ]  # fmt: skip
    built = ["audit", "catalog", "core", "expenses", "sales"]
    with pg.engine.begin() as connection:
        full = _insert(connection, every)
        untouched = _insert(connection, built)
        _upgrade(connection)
        _upgrade(connection)  # idempotente
        found = connection.execute(sa.select(shop_table.c.id, shop_table.c.enabled_modules))
        rows = {row.id: row.enabled_modules for row in found}
    assert rows[full] == [
        "audit", "catalog", "core", "dashboard", "expenses", "purchases", "receivables", "sales",
    ]  # fmt: skip
    assert rows[untouched] == built
