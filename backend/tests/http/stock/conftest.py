"""Application complète avec le catalogue et le stock (identité, journal, socle) en mémoire."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.bootstrap.catalog import build_catalog
from app.bootstrap.config import Settings
from app.bootstrap.container import http_config_from
from app.bootstrap.core import build_core
from app.bootstrap.identity import build_identity
from app.bootstrap.journal import build_journal
from app.bootstrap.shops import build_shops
from app.bootstrap.stock import build_stock
from app.domain.identity.phone import PhoneNumber
from app.domain.identity.user import User
from app.infrastructure.persistence.memory.clock import FixedClock
from app.interface.http.app import create_app
from tests.application.identity.support import PASSWORD, T0, FakeHasher
from tests.application.shops.support import FixedPins
from tests.http.shops.conftest import ADMIN_PHONE, Api


@pytest.fixture
def api(settings: Settings) -> Iterator[Api]:
    clock = FixedClock(T0)
    hasher = FakeHasher()
    core = build_core(settings, clock)
    identity = build_identity(settings, hasher=hasher, core=core)
    journal = build_journal(settings, clock=clock, guard=identity.auth.guard, core=core)
    shops = build_shops(identity, pins=FixedPins())
    catalog = build_catalog(identity)
    stock = build_stock(identity)
    app = create_app(
        http_config_from(settings),
        identity.auth,
        journal.http,
        shops.http,
        catalog=catalog.http,
        stock=stock.http,
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
    with TestClient(app, base_url="https://testserver", raise_server_exceptions=False) as client:
        yield Api(client, identity)
