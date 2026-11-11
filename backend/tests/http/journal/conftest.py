"""Application complète (identité + journal) en mémoire : horloge figée, Argon2 allégé."""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import httpx2 as httpx
import pytest
from fastapi.testclient import TestClient

from app.application.security.roles import Role
from app.bootstrap.config import Settings
from app.bootstrap.container import http_config_from
from app.bootstrap.identity import IdentityModule, build_identity
from app.bootstrap.journal import JournalModule, build_journal
from app.domain.identity.phone import PhoneNumber
from app.domain.identity.user import User
from app.domain.shared.ids import DeviceId, ShopId
from app.infrastructure.auth.argon2_hasher import Argon2PasswordHasher
from app.infrastructure.persistence.memory.clock import FixedClock
from app.interface.http.app import create_app
from tests.application.identity.support import PIN, T0

PREFIX = "/api/v1"


@dataclass
class Member:
    user: User
    device: DeviceId
    token: str


@dataclass
class Shop:
    client: TestClient
    identity: IdentityModule
    journal: JournalModule
    shop_id: ShopId

    def member(self, phone: str, role: Role) -> Member:
        user = User.register(
            phone=PhoneNumber.parse(phone),
            name="Paul",
            secret_hash=self.identity.hasher.hash(PIN),
            must_change_pin=False,
        )
        with self.identity.uow_factory() as uow:
            uow.users.add(user)
            uow.commit()
        self.identity.memberships.grant(user.id, self.shop_id, "Motos Garoua", role)
        device = DeviceId.new()
        response = self.client.post(
            f"{PREFIX}/auth/login",
            json={"phone": phone, "pin": PIN, "device_label": "Android — Chrome"},
            headers={"X-Device-Id": str(device)},
        )
        assert response.status_code == 200, response.text
        return Member(user, device, response.json()["access_token"])

    def call(self, method: str, path: str, who: Member, **params: Any) -> httpx.Response:
        return self.client.request(
            method,
            f"{PREFIX}/shops/{self.shop_id}{path}",
            params=params,
            headers={"X-Device-Id": str(who.device), "Authorization": f"Bearer {who.token}"},
        )


@pytest.fixture
def shop(settings: Settings) -> Iterator[Shop]:
    clock = FixedClock(T0)
    hasher = Argon2PasswordHasher(time_cost=1, memory_cost_kib=8, parallelism=1)
    identity = build_identity(settings, clock=clock, hasher=hasher)
    journal = build_journal(settings, clock=clock, guard=identity.auth.guard)
    app = create_app(http_config_from(settings), identity.auth, journal.http)
    with TestClient(app, base_url="https://testserver", raise_server_exceptions=False) as client:
        yield Shop(client, identity, journal, ShopId.new())
