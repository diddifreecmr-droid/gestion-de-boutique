"""Application complète (tous les modules du Lot 1, dont le Tableau de bord) en mémoire, horloge
contrôlable : `desk.at(instant)` déplace l'horloge et rouvre les sessions (jetons de 15 min)."""

from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.bootstrap.catalog import build_catalog
from app.bootstrap.config import Settings
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
from app.domain.identity.phone import PhoneNumber
from app.domain.identity.user import User
from app.infrastructure.persistence.memory.clock import FixedClock
from app.interface.http.app import create_app
from tests.application.identity.support import PASSWORD, FakeHasher
from tests.application.shops.support import FixedPins
from tests.http.catalog.test_catalog_http import OWNER_PHONE, STAFF, Shop
from tests.http.shops.conftest import ADMIN_PHONE, NEW_PIN, Api, Session

START = datetime(2026, 11, 5, 8, 0, tzinfo=UTC)


@dataclass
class Desk:
    """Boutique « Motos Garoua » ouverte le 05/11 ; sessions du propriétaire et du personnel."""

    api: Api
    clock: FixedClock
    shop: Shop = field(init=False)

    def __post_init__(self) -> None:
        self.shop = Shop(self.api)

    @property
    def owner(self) -> Session:
        return self.shop.owner

    def staff(self, role: str) -> Session:
        return self.shop.staff[role]

    def at(self, instant: datetime) -> None:
        self.clock.move_to(instant)
        self.shop.owner = self.api.login(OWNER_PHONE, NEW_PIN)
        for role, phone in STAFF.items():
            self.shop.staff[role] = self.api.login(phone, NEW_PIN)

    def call(self, method: str, suffix: str, who: Session, **kwargs: Any) -> Any:
        return self.shop.call(method, suffix, who, **kwargs)

    def ok(self, method: str, suffix: str, who: Session, **kwargs: Any) -> Any:
        response = self.call(method, suffix, who, **kwargs)
        assert response.status_code in (200, 201), response.text
        return response.json()

    def mode(self, name: str) -> str:
        modes = self.ok("GET", "/payment-modes", self.owner)
        return str(next(m["id"] for m in modes if m["name"] == name))

    def category(self, name: str) -> str:
        found = self.ok("GET", "/expense-categories", self.owner)
        return str(next(c["id"] for c in found if c["name"] == name))


@pytest.fixture
def desk(settings: Settings) -> Iterator[Desk]:
    clock = FixedClock(START)
    hasher = FakeHasher()
    core = build_core(settings, clock)
    identity = build_identity(settings, hasher=hasher, core=core)
    journal = build_journal(settings, clock=clock, guard=identity.auth.guard, core=core)
    shops = build_shops(identity, pins=FixedPins())
    stock = build_stock(identity)
    app = create_app(
        http_config_from(settings),
        identity.auth,
        journal.http,
        shops.http,
        catalog=build_catalog(identity, ranking=sales_ranking(clock)).http,
        expenses=build_expenses(identity).http,
        stock=stock.http,
        purchasing=build_purchasing(identity, stock.ledger).http,
        sales=build_sales(identity, stock.ledger).http,
        receivables=build_receivables(identity).http,
        reporting=build_reporting(identity).http,
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
        yield Desk(Api(client, identity), clock)
