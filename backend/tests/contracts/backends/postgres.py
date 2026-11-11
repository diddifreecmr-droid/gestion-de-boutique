"""Adaptateur PostgreSQL sous contrat : base `TEST_DATABASE_URL`, vidée à chaque test.

`prepare()` (appelé une fois par session avec `--backend=postgres`) valide l'URL, vérifie que
la base répond, applique les migrations et crée la table de démonstration. Tout échec lève
`pytest.UsageError` : la session échoue, elle ne saute rien.
"""

import os

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import make_url

from app.infrastructure.persistence.sqlalchemy.engine import create_sql_engine
from tests.contracts.backends.sql import SqlContractBackend, migrate

URL_VARIABLE = "TEST_DATABASE_URL"
POOL_SIZE = 24  # > 20 transactions concurrentes des tests de concurrence (A8)
LOCK_TIMEOUT = "-c lock_timeout=15s"  # détail PostgreSQL (tests) : un interblocage échoue
CONNECT_TIMEOUT_S = 5  # base injoignable : échec rapide plutôt que blocage

_engines: dict[str, sa.Engine] = {}  # un seul moteur par session pytest


def database_url_from_env() -> str:
    """URL de la base de test ; refuse toute base dont le nom ne contient pas « test »."""
    url = os.environ.get(URL_VARIABLE, "").strip()
    if not url:
        msg = (
            f"--backend=postgres : variable {URL_VARIABLE} absente "
            "(ex. postgresql+psycopg://boutique:…@127.0.0.1:5432/boutique_test, "
            "voir infra/README.md)"
        )
        raise pytest.UsageError(msg)
    database = make_url(url).database or ""
    if "test" not in database:
        msg = f"{URL_VARIABLE} doit viser une base de test (nom contenant « test ») : {database!r}"
        raise pytest.UsageError(msg)
    return url


def prepare() -> sa.Engine:
    url = database_url_from_env()
    if url in _engines:
        return _engines[url]
    engine = create_sql_engine(
        url,
        pool_size=POOL_SIZE,
        connect_args={"options": LOCK_TIMEOUT, "connect_timeout": CONNECT_TIMEOUT_S},
    )
    try:
        migrate(engine)
    except sa.exc.OperationalError as exc:
        engine.dispose()
        msg = f"--backend=postgres : base de test injoignable ({exc.orig})"
        raise pytest.UsageError(msg) from exc
    _engines[url] = engine
    return engine


def dispose() -> None:
    while _engines:
        _, engine = _engines.popitem()
        engine.dispose()


class PostgresContractBackend(SqlContractBackend):
    def __init__(self) -> None:
        super().__init__(prepare())
