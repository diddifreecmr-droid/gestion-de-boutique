"""Migration `0019_import_batches` sur PostgreSQL, **isolée** de la tête de chaîne.

Sa précédente `0018_exchange_rights` (T29) est développée en parallèle : le test ne dépend pas
d'elle. Dans un schéma PostgreSQL jetable, la chaîne réelle est appliquée jusqu'à `0017` (copie
des fichiers `0001` à `0017`), puis `0019` seule : tables, contraintes nommées, unicités par
boutique, index ; puis retour arrière (tables supprimées) et ré-application.
"""

import importlib.util
import shutil
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic.config import Config
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext

from alembic import command
from tests.contracts.backends.postgres import database_url_from_env
from tests.infrastructure.postgres.conftest import REASON

ROOT = Path(__file__).parents[3]
VERSIONS = ROOT / "alembic" / "versions"
MIGRATION = VERSIONS / "0019_import_batches.py"
UP_TO = "0017_upcoming_modules"


def _migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("import_batches", MIGRATION)
    if spec is None or spec.loader is None:
        msg = f"Migration illisible : {MIGRATION}"
        raise RuntimeError(msg)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def at_0017(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[sa.Connection]:
    """Connexion sur un schéma neuf migré jusqu'à 0017 ; schéma supprimé à la fin."""
    if request.config.getoption("--backend") != "postgres":
        pytest.skip(REASON)
    for path in sorted(VERSIONS.glob("00*.py")):
        if path.name[:4] <= "0017":
            shutil.copy(path, tmp_path / path.name)
    schema = f"t32_{uuid4().hex[:12]}"
    engine = sa.create_engine(database_url_from_env(), poolclass=sa.pool.NullPool)
    try:
        with engine.connect() as connection:
            connection.execute(sa.text(f'CREATE SCHEMA "{schema}"'))
            connection.execute(sa.text(f'SET search_path TO "{schema}"'))
            connection.commit()
            config = Config(str(ROOT / "alembic.ini"))
            config.set_main_option("script_location", str(ROOT / "alembic"))
            config.set_main_option("version_locations", str(tmp_path))
            config.attributes["connection"] = connection
            command.upgrade(config, UP_TO)
            connection.commit()
            yield connection
            connection.rollback()
            connection.execute(sa.text(f'DROP SCHEMA "{schema}" CASCADE'))
            connection.commit()
    finally:
        engine.dispose()


def _run(connection: sa.Connection, step: str) -> None:
    with Operations.context(MigrationContext.configure(connection)):
        getattr(_migration(), step)()
    connection.commit()


def test_upgrade_creates_the_tables_then_downgrade_removes_them(at_0017: sa.Connection) -> None:
    connection = at_0017
    version = connection.execute(sa.text("SELECT version_num FROM alembic_version")).scalar()
    assert version == UP_TO
    module = _migration()
    assert (module.revision, module.down_revision) == (
        "0019_import_batches",
        "0018_exchange_rights",
    )
    _run(connection, "upgrade")
    inspector = sa.inspect(connection)
    assert {"import_batch", "import_item"} <= set(inspector.get_table_names())
    checks = {c["name"] for c in inspector.get_check_constraints("import_batch")}
    assert checks == {
        "import_batch_version_positive_check", "import_batch_rows_balanced_check",
        "import_batch_status_known_check",
    }  # fmt: skip
    uniques = {u["name"] for u in inspector.get_unique_constraints("import_batch")}
    assert uniques == {"import_batch_number", "import_batch_preview"}
    assert {i["name"] for i in inspector.get_indexes("import_item")} == {
        "import_item_shop_entity_idx"
    }
    shop, preview = uuid4(), uuid4()
    row = {
        "shop": shop, "preview": preview, "number": "IMP-000001", "read": 2, "imported": 1,
        "ignored": 1, "status": "imported",
    }  # fmt: skip
    insert = sa.text(
        "INSERT INTO import_batch (id, shop_id, version, number, kind, preview_id,"
        " source_file_key, rows_read, rows_imported, rows_ignored, status, imported_by,"
        " imported_at) VALUES (gen_random_uuid(), :shop, 1, :number, 'articles', :preview,"
        " 'k', :read, :imported, :ignored, :status, gen_random_uuid(), now())"
    )
    connection.execute(insert, row)
    connection.commit()
    refused = [
        {**row, "preview": uuid4()},  # même numéro dans la boutique
        {**row, "number": "IMP-000002"},  # même aperçu
        {**row, "number": "IMP-000003", "preview": uuid4(), "read": 3},  # compteurs faux
        {**row, "number": "IMP-000004", "preview": uuid4(), "status": "deleted"},
    ]
    for values in refused:
        with pytest.raises(sa.exc.IntegrityError):
            connection.execute(insert, values)
        connection.rollback()
    connection.execute(insert, {**row, "shop": uuid4()})  # autre boutique : permis
    connection.commit()
    _run(connection, "downgrade")
    assert not {"import_batch", "import_item"} & set(sa.inspect(connection).get_table_names())
    _run(connection, "upgrade")  # ré-application après retour arrière
    assert "import_batch" in sa.inspect(connection).get_table_names()
