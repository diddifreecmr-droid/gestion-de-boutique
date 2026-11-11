"""Base SQLite fichier, migrée par Alembic une fois par session, vidée à chaque test.

SQLite n'est pas une cible de production : il sert à exécuter **le même** adaptateur SQL sans
serveur (la suite par défaut ne dépend d'aucune base). `pysqlite` gère mal les transactions
(pas de `BEGIN` émis, savepoints cassés) : la recette documentée de SQLAlchemy ci-dessous lui
rend un comportement transactionnel standard. Ce réglage reste dans les tests.
"""

from collections.abc import Iterator
from typing import Any

import pytest
import sqlalchemy as sa

from app.domain.shared.ids import ShopId
from app.infrastructure.persistence.sqlalchemy.engine import create_sql_engine
from tests.contracts.backends.sql import SqlContractBackend, migrate


def sqlite_engine(path: str) -> sa.Engine:
    engine = create_sql_engine(f"sqlite:///{path}", isolation_level="SERIALIZABLE")

    @sa.event.listens_for(engine, "connect")
    def _no_implicit_transactions(dbapi_connection: Any, _record: object) -> None:
        dbapi_connection.isolation_level = None

    @sa.event.listens_for(engine, "begin")
    def _explicit_begin(connection: sa.Connection) -> None:
        connection.exec_driver_sql("BEGIN")

    return engine


@pytest.fixture(scope="session")
def sqlite_db(tmp_path_factory: pytest.TempPathFactory) -> Iterator[sa.Engine]:
    engine = sqlite_engine(str(tmp_path_factory.mktemp("sql") / "contracts.db"))
    migrate(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def backend(sqlite_db: sa.Engine) -> SqlContractBackend:
    return SqlContractBackend(sqlite_db)


@pytest.fixture
def shop_a() -> ShopId:
    return ShopId.new()


@pytest.fixture
def shop_b() -> ShopId:
    return ShopId.new()
