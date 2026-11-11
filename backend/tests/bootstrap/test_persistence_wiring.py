"""Composition root : `PERSISTENCE_BACKEND` choisit la fabrique d'unités de travail."""

import pytest
from pydantic import SecretStr

from app.bootstrap.config import Environment, PersistenceBackend, Settings
from app.bootstrap.container import build_app
from app.bootstrap.persistence import build_unit_of_work_factory
from app.infrastructure.persistence.memory.uow import MemoryUnitOfWorkFactory
from app.infrastructure.persistence.sqlalchemy.engine import create_sql_engine
from app.infrastructure.persistence.sqlalchemy.uow import SqlUnitOfWorkFactory

URL = "postgresql+psycopg://boutique:secret@127.0.0.1:5432/boutique"


def test_memory_backend_builds_a_memory_factory() -> None:
    settings = Settings(ENVIRONMENT=Environment.TEST, _env_file=None)
    assert isinstance(build_unit_of_work_factory(settings), MemoryUnitOfWorkFactory)


def test_postgres_backend_builds_a_lazy_sql_factory() -> None:
    settings = Settings(
        ENVIRONMENT=Environment.TEST,
        PERSISTENCE_BACKEND=PersistenceBackend.POSTGRES,
        DATABASE_URL=SecretStr(URL),
        _env_file=None,
    )
    factory = build_unit_of_work_factory(settings)
    assert isinstance(factory, SqlUnitOfWorkFactory)
    assert factory.engine.url.database == "boutique"  # aucune connexion ouverte
    assert factory.engine.dialect.name == "postgresql"
    factory.engine.dispose()


def test_postgres_guard_without_url() -> None:
    settings = Settings.model_construct(  # contourne la validation : garde-fou testé
        ENVIRONMENT=Environment.TEST, PERSISTENCE_BACKEND=PersistenceBackend.POSTGRES
    )
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        build_unit_of_work_factory(settings)


def test_build_app_exposes_the_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.delenv("PERSISTENCE_BACKEND", raising=False)
    app = build_app(env_file=None)
    assert isinstance(app.state.uow_factory, MemoryUnitOfWorkFactory)


def test_empty_url_is_refused() -> None:
    with pytest.raises(ValueError, match="vide"):
        create_sql_engine("  ")
