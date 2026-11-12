"""Banc de recette T24 : l'application **complète** du Lot 1, assemblée comme `build_app`.

Mêmes modules que la composition root (`app/bootstrap/container.py`), avec une horloge figée,
un hachage factice et des codes provisoires fixes. `--backend=postgres` fait tourner les mêmes
tests HTTP sur PostgreSQL (`TEST_DATABASE_URL`, base vidée avant chaque test) :

    uv run pytest tests/http/recette                        # mémoire
    uv run pytest tests/http/recette --backend=postgres     # PostgreSQL
"""

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.bootstrap.catalog import build_catalog
from app.bootstrap.config import Environment, PersistenceBackend, Settings
from app.bootstrap.container import http_config_from
from app.bootstrap.core import build_core
from app.bootstrap.expenses import build_expenses
from app.bootstrap.identity import build_identity
from app.bootstrap.journal import build_journal
from app.bootstrap.purchasing import build_purchasing
from app.bootstrap.receivables import build_receivables
from app.bootstrap.reporting import build_reporting
from app.bootstrap.sales import build_sales, sales_ranking
from app.bootstrap.shops import build_shops
from app.bootstrap.stock import build_stock
from app.bootstrap.sync import build_sync
from app.domain.identity.phone import PhoneNumber
from app.domain.identity.user import User
from app.infrastructure.persistence.memory.clock import FixedClock
from app.infrastructure.persistence.sqlalchemy.uow import SqlUnitOfWorkFactory
from app.interface.http.app import create_app
from tests.application.identity.support import PASSWORD, FakeHasher
from tests.application.shops.support import FixedPins
from tests.contracts.backends import build_backend
from tests.contracts.backends.postgres import database_url_from_env
from tests.http.recette.world import World
from tests.http.shops.conftest import ADMIN_PHONE, Api

NOW = datetime(2026, 11, 10, 9, 0, tzinfo=UTC)  # mardi 10/11/2026 10:00 à Douala


def _settings(backend: str) -> Settings:
    if backend == "memory":
        return Settings(ENVIRONMENT=Environment.TEST, _env_file=None)
    build_backend(backend)  # base de test migrée puis vidée
    return Settings(
        ENVIRONMENT=Environment.TEST,
        PERSISTENCE_BACKEND=PersistenceBackend.POSTGRES,
        DATABASE_URL=database_url_from_env(),
        _env_file=None,
    )


@pytest.fixture
def lot1(request: pytest.FixtureRequest) -> Iterator[Api]:
    settings = _settings(str(request.config.getoption("--backend")))
    clock = FixedClock(NOW)
    hasher = FakeHasher()
    core = build_core(settings, clock)
    identity = build_identity(settings, hasher=hasher, core=core)
    journal = build_journal(settings, clock=clock, guard=identity.auth.guard, core=core)
    stock = build_stock(identity)
    sales = build_sales(identity, stock.ledger)
    expenses = build_expenses(identity)
    app = create_app(
        http_config_from(settings),
        identity.auth,
        journal.http,
        build_shops(identity, pins=FixedPins()).http,
        catalog=build_catalog(identity, ranking=sales_ranking(clock)).http,
        expenses=expenses.http,
        stock=stock.http,
        purchasing=build_purchasing(identity, stock.ledger).http,
        sales=sales.http,
        receivables=build_receivables(identity).http,
        reporting=build_reporting(identity).http,
        sync=build_sync(identity, journal, sales, expenses).http,
    )
    admin = User.register(
        phone=PhoneNumber.parse(ADMIN_PHONE),
        name="Admin",
        secret_hash=hasher.hash(PASSWORD),
        is_platform_admin=True,
        must_change_pin=False,
    )
    with core.platform_uow_factory() as uow:
        uow.users.add(admin)
        uow.commit()
    try:
        with TestClient(app, base_url="https://testserver", raise_server_exceptions=False) as c:
            yield Api(c, identity)
    finally:
        if isinstance(core.shop_uow_factory, SqlUnitOfWorkFactory):
            core.shop_uow_factory.engine.dispose()


@pytest.fixture
def world(lot1: Api) -> World:
    """Boutiques A et B remplies (voir `world.py`)."""
    return World.build(lot1)
