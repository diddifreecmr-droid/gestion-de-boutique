"""Migration `0018_exchange_rights` (T29, QC-4) sur PostgreSQL : la colonne
`shop_settings.employee_exchange_allowed` est ajoutée **fausse** pour une boutique existante,
non nulle ; le retour arrière la retire puis la montée la remet."""

import importlib.util
from pathlib import Path
from types import ModuleType
from uuid import uuid4

import sqlalchemy as sa
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext

from app.infrastructure.persistence.sqlalchemy.tables_shops import shop as shop_table
from tests.contracts.backends.postgres import PostgresContractBackend

MIGRATION = Path(__file__).parents[3] / "alembic" / "versions" / "0018_exchange_rights.py"
COLUMN = "employee_exchange_allowed"

# Réglages tels qu'avant 0018 (sans la colonne) : écrits entre le retour arrière et la montée.
_settings = sa.table(
    "shop_settings",
    *(sa.column(name) for name in ("id", "shop_id", "version", "receipt_format")),
    *(sa.column(name) for name in ("paper_width_mm", "printable_width_mm", "margin_mm")),
    *(sa.column(name) for name in ("font_size_pt", "show_logo", "copies")),
    *(sa.column(name) for name in ("low_stock_threshold", "min_price_enabled")),
)


def _migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("exchange_rights", MIGRATION)
    if spec is None or spec.loader is None:
        msg = f"Migration illisible : {MIGRATION}"
        raise RuntimeError(msg)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _columns(connection: sa.Connection) -> dict[str, dict[str, object]]:
    return {c["name"]: dict(c) for c in sa.inspect(connection).get_columns("shop_settings")}


def _old_shop(connection: sa.Connection) -> object:
    shop_id = uuid4()
    connection.execute(
        shop_table.insert().values(
            id=shop_id, shop_id=shop_id, version=1, account_id=uuid4(), name=f"B {shop_id}",
            profile_code="pret_a_porter", city="Douala", phone="+237222000000",
            enabled_modules=["audit", "catalog", "core", "sales"], status="active",
            created_at=sa.func.now(),
        )
    )  # fmt: skip
    connection.execute(
        _settings.insert().values(
            id=uuid4(), shop_id=shop_id, version=1, receipt_format="58mm", paper_width_mm=58,
            printable_width_mm=48, margin_mm=2, font_size_pt=9, show_logo=False, copies=1,
            low_stock_threshold=2, min_price_enabled=False,
        )
    )  # fmt: skip
    return shop_id


def test_downgrade_then_upgrade_adds_a_false_column(pg: PostgresContractBackend) -> None:
    migration = _migration()
    assert (migration.revision, migration.down_revision) == (
        "0018_exchange_rights",
        "0017_upcoming_modules",
    )
    with (
        pg.engine.begin() as connection,
        Operations.context(MigrationContext.configure(connection)),
    ):
        assert COLUMN in _columns(connection)  # base de test déjà à la tête
        migration.downgrade()
        assert COLUMN not in _columns(connection)
        shop_id = _old_shop(connection)
        migration.upgrade()
        column = _columns(connection)[COLUMN]
        stored = connection.execute(
            sa.text(f"SELECT {COLUMN} FROM shop_settings WHERE shop_id = :shop"),
            {"shop": shop_id},
        ).scalar_one()
        connection.execute(sa.text("DELETE FROM shop_settings WHERE shop_id = :s"), {"s": shop_id})
        connection.execute(shop_table.delete().where(shop_table.c.id == shop_id))
    assert column["nullable"] is False
    assert stored is False
