"""Application complète avec le module Dépenses (mémoire, horloge figée, hachage factice).

`shop` : « Motos Garoua » ouverte, sessions du propriétaire, du comptable et du vendeur.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import httpx2 as httpx
import pytest
from fastapi.testclient import TestClient

from app.bootstrap.config import Settings
from app.bootstrap.container import http_config_from
from app.bootstrap.core import build_core
from app.bootstrap.expenses import build_expenses
from app.bootstrap.identity import build_identity
from app.bootstrap.journal import build_journal
from app.bootstrap.shops import build_shops
from app.domain.identity.phone import PhoneNumber
from app.domain.identity.user import User
from app.infrastructure.persistence.memory.clock import FixedClock
from app.interface.http.app import create_app
from tests.application.identity.support import PASSWORD, T0, FakeHasher
from tests.application.shops.support import FixedPins
from tests.http.shops.conftest import ADMIN_PHONE, NEW_PIN, PREFIX, Api, Session

OWNER_PHONE = "690000001"
ACCOUNTANT_PHONE = "677000003"


@dataclass
class ExpenseShop:
    api: Api
    clock: FixedClock
    shop_id: str
    owner: Session
    accountant: Session
    seller: Session

    def call(
        self,
        method: str,
        suffix: str,
        who: Session,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        auth = {"X-Device-Id": str(who.device), "Authorization": f"Bearer {who.token}"}
        url = f"{PREFIX}/shops/{self.shop_id}{suffix}"
        return self.api.client.request(method, url, headers=auth | (headers or {}), **kwargs)

    def relogin(self) -> None:
        """Nouvelles sessions après un saut d'horloge (jetons d'accès de 15 min)."""
        self.owner = self.api.login(OWNER_PHONE, NEW_PIN)
        self.accountant = self.api.login(ACCOUNTANT_PHONE, NEW_PIN)

    def category(self, name: str) -> str:
        found = self.call("GET", "/expense-categories", self.owner).json()
        return str(next(c["id"] for c in found if c["name"] == name))


def _member(api: Api, owner: Session, shop_id: str, phone: str, role: str) -> Session:
    body: dict[str, Any] = {"name": role, "phone": phone, "role": role}
    if role == "seller":
        places = api.call("GET", f"/shops/{shop_id}/locations", owner).json()["items"]
        body["default_location_id"] = next(p["id"] for p in places if p["name"] == "Garoua")
    added = api.call("POST", f"/shops/{shop_id}/members", owner, json=body)
    assert added.status_code == 201, added.text
    return api.login(phone, added.json()["temporary_pin"])


@pytest.fixture
def shop(settings: Settings) -> Iterator[ExpenseShop]:
    clock = FixedClock(T0)
    hasher = FakeHasher()
    core = build_core(settings, clock)
    identity = build_identity(settings, hasher=hasher, core=core)
    journal = build_journal(settings, clock=clock, guard=identity.auth.guard, core=core)
    shops = build_shops(identity, pins=FixedPins())
    expenses = build_expenses(identity)
    app = create_app(
        http_config_from(settings), identity.auth, journal.http, shops.http, expenses=expenses.http
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
        api = Api(client, identity)
        opened = api.open_motos(api.admin(), OWNER_PHONE)
        shop_id = opened["shop"]["shop_id"]
        owner = api.login(OWNER_PHONE, opened["temporary_pin"])
        yield ExpenseShop(
            api=api,
            clock=clock,
            shop_id=shop_id,
            owner=owner,
            accountant=_member(api, owner, shop_id, ACCOUNTANT_PHONE, "accountant"),
            seller=_member(api, owner, shop_id, "677000002", "seller"),
        )
