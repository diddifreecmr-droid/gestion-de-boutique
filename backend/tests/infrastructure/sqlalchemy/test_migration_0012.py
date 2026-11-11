"""Migration 0012 : réglage d'accord faux pour les boutiques existantes, nom d'article unique —
une base qui a déjà des articles de même nom fait **échouer** la migration (rien n'est modifié)."""

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.config import Config

from alembic import command
from app.infrastructure.persistence.sqlalchemy.tables_catalog import article
from tests.contracts.backends.sql import ALEMBIC_INI
from tests.infrastructure.sqlalchemy.conftest import sqlite_engine


def _upgrade(engine: sa.Engine, revision: str) -> None:
    config = Config(str(ALEMBIC_INI))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, revision)


def _article(shop_id: uuid.UUID, name: str, model: str | None = None) -> dict[str, object]:
    return {
        "id": uuid.uuid4(),
        "shop_id": shop_id,
        "version": 1,
        "display_name": name,
        "model": model,
        "search_key": name.lower(),
        "sort_key": name.lower(),
        "stock_unit": "PIECE",
        "sold_by_piece": False,
        "attributes": {},
        "status": "active",
        "created_at": datetime(2026, 11, 1, tzinfo=UTC),
    }


def _insert(engine: sa.Engine, *rows: dict[str, object]) -> None:
    with engine.begin() as connection:
        connection.execute(article.insert(), list(rows))  # colonnes de 0011 seulement


def test_existing_articles_get_their_name_key(tmp_path: Path) -> None:
    engine = sqlite_engine(str(tmp_path / "ok.db"))
    _upgrade(engine, "0011_reporting_indexes")
    shop = uuid.uuid4()
    _insert(
        engine,
        _article(shop, "Chemise"),
        _article(shop, "Haojue HJ125", model="HJ125"),
        _article(shop, "Haojue HJ125 bis", model="HJ125"),  # motos : nom non contraint
        _article(uuid.uuid4(), "CHEMISE"),  # autre boutique
    )
    _upgrade(engine, "head")
    with engine.connect() as connection:
        keys = connection.execute(sa.text("SELECT display_name, name_key FROM article")).all()
    assert sorted(keys, key=str) == sorted(
        [("Chemise", "chemise"), ("CHEMISE", "chemise"),
         ("Haojue HJ125", None), ("Haojue HJ125 bis", None)],
        key=str,
    )  # fmt: skip
    engine.dispose()


def test_duplicate_names_stop_the_migration(tmp_path: Path) -> None:
    engine = sqlite_engine(str(tmp_path / "dup.db"))
    _upgrade(engine, "0011_reporting_indexes")
    _insert(engine, _article(uuid.uuid4(), "Robe"), *(
        _article(shop := uuid.uuid4(), "Jupe Wax"), _article(shop, "  jupe-wax ")
    ))  # fmt: skip
    with pytest.raises(RuntimeError, match="renommez-les") as stopped:
        _upgrade(engine, "head")
    assert "Jupe Wax" in str(stopped.value)
    assert "jupe-wax" in str(stopped.value)
    assert "Robe" not in str(stopped.value)
    with engine.connect() as connection:
        columns = {c["name"] for c in sa.inspect(connection).get_columns("article")}
    assert "name_key" not in columns  # transaction annulée : base intacte
    engine.dispose()
