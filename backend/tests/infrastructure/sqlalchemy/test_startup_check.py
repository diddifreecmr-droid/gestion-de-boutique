"""Vérification de la base au démarrage de l'API (T25, fail-fast).

SQLite en mémoire suffit pour les cas « non migrée / sans révision / migrée » (le contrôle
n'emploie que du SQL portable) ; « injoignable » vise un port local fermé.
"""

import pytest
import sqlalchemy as sa

from app.bootstrap.container import build_app
from app.infrastructure.persistence.sqlalchemy.startup import DatabaseUnavailable, verify_database

CLOSED_PORT_URL = "postgresql+psycopg://boutique:tres-secret@127.0.0.1:1/boutique"


def _sqlite(*statements: str) -> sa.Engine:
    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(sa.text(statement))
    return engine


def test_migrated_database_returns_its_revision() -> None:
    engine = _sqlite(
        "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)",
        "INSERT INTO alembic_version VALUES ('0042_dernière')",
    )
    assert verify_database(engine) == "0042_dernière"


def test_database_without_migrations_is_refused() -> None:
    with pytest.raises(DatabaseUnavailable, match="non migrée"):
        verify_database(_sqlite())


def test_database_with_empty_revision_table_is_refused() -> None:
    engine = _sqlite("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
    with pytest.raises(DatabaseUnavailable, match="sans révision"):
        verify_database(engine)


def test_unreachable_database_is_refused_without_leaking_the_password() -> None:
    engine = sa.create_engine(CLOSED_PORT_URL, connect_args={"connect_timeout": 2})
    with pytest.raises(DatabaseUnavailable, match="injoignable") as caught:
        verify_database(engine)
    assert "tres-secret" not in str(caught.value)
    assert "127.0.0.1:1/boutique" in str(caught.value)
    engine.dispose()


def test_api_refuses_to_start_when_the_database_is_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "prod")
    monkeypatch.setenv("DATABASE_URL", f"{CLOSED_PORT_URL}?connect_timeout=2")
    monkeypatch.delenv("PERSISTENCE_BACKEND", raising=False)
    with pytest.raises(DatabaseUnavailable, match="injoignable"):
        build_app(env_file=None)
