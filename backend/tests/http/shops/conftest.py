"""Application complète (identité, journal, socle) en mémoire : horloge figée, hachage factice."""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import httpx2 as httpx
import pytest
from fastapi.testclient import TestClient

from app.bootstrap.config import Settings
from app.bootstrap.container import http_config_from
from app.bootstrap.core import build_core
from app.bootstrap.identity import IdentityModule, build_identity
from app.bootstrap.journal import build_journal
from app.bootstrap.shops import build_shops
from app.domain.identity.phone import PhoneNumber
from app.domain.identity.user import User
from app.domain.shared.ids import DeviceId
from app.infrastructure.persistence.memory.clock import FixedClock
from app.interface.http.app import create_app
from tests.application.identity.support import PASSWORD, PIN, T0, FakeHasher
from tests.application.shops.support import FixedPins

PREFIX = "/api/v1"
ADMIN_PHONE = "600000001"
NEW_PIN = "730184"


@dataclass
class Session:
    device: DeviceId
    token: str


@dataclass
class Api:
    client: TestClient
    identity: IdentityModule

    def login(self, phone: str, secret: str = PIN, *, admin: bool = False) -> Session:
        device = DeviceId.new()
        key = "password" if admin else "pin"
        response = self.client.post(
            f"{PREFIX}/auth/login",
            json={"phone": phone, key: secret, "device_label": "PC"},
            headers={"X-Device-Id": str(device)},
        )
        assert response.status_code == 200, response.text
        session = Session(device, response.json()["access_token"])
        if response.json()["must_change_pin"]:
            changed = self.call("POST", "/auth/change-pin", session, json={
                "current_pin": secret, "new_pin": NEW_PIN, "new_pin_confirmation": NEW_PIN,
            })  # fmt: skip
            assert changed.status_code == 204, changed.text
        return session

    def admin(self) -> Session:
        return self.login(ADMIN_PHONE, PASSWORD, admin=True)

    def call(self, method: str, path: str, who: Session, **kwargs: Any) -> httpx.Response:
        headers = {"X-Device-Id": str(who.device), "Authorization": f"Bearer {who.token}"}
        return self.client.request(method, f"{PREFIX}{path}", headers=headers, **kwargs)

    def open_motos(self, admin: Session, owner_phone: str = "690000001") -> dict[str, Any]:
        body = {
            "profile_code": "motos",
            "name": "Motos Garoua",
            "city": "Garoua",
            "phone": "222000000",
            "owner": {"name": "Moussa", "phone": owner_phone},
        }
        response = self.call("POST", "/platform/shops", admin, json=body)
        assert response.status_code == 201, response.text
        result: dict[str, Any] = response.json()
        return result


@pytest.fixture
def api(settings: Settings) -> Iterator[Api]:
    clock = FixedClock(T0)
    hasher = FakeHasher()
    core = build_core(settings, clock)
    identity = build_identity(settings, hasher=hasher, core=core)
    journal = build_journal(settings, clock=clock, guard=identity.auth.guard, core=core)
    shops = build_shops(identity, pins=FixedPins())
    app = create_app(http_config_from(settings), identity.auth, journal.http, shops.http)
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
