"""Application HTTP assemblée par la composition root, avec horloge figée et Argon2 allégé."""

from dataclasses import dataclass

import httpx2 as httpx
from fastapi.testclient import TestClient

from app.application.security.roles import Role
from app.bootstrap.identity import IdentityModule
from app.domain.identity.phone import PhoneNumber
from app.domain.identity.user import User
from app.domain.shared.ids import DeviceId, ShopId
from app.infrastructure.persistence.memory.clock import FixedClock
from tests.application.identity.support import PIN
from tests.support.shops import grant

SHOP = ShopId.new()
PREFIX = "/api/v1"


@dataclass
class Api:
    client: TestClient
    module: IdentityModule
    clock: FixedClock

    def register(
        self, phone: str = "677001122", secret: str = PIN, *, must_change: bool = False
    ) -> User:
        user = User.register(
            phone=PhoneNumber.parse(phone),
            name="Awa Bello",
            secret_hash=self.module.hasher.hash(secret),
            must_change_pin=must_change,
        )
        with self.module.uow_factory() as uow:
            uow.users.add(user)
            uow.commit()
        grant(self.module.core.shop_uow_factory, user.id, SHOP, Role.SELLER)
        return user

    def login(self, device: DeviceId, phone: str = "677001122", pin: str = PIN) -> httpx.Response:
        return self.client.post(
            f"{PREFIX}/auth/login",
            json={"phone": phone, "pin": pin, "device_label": "Android — Chrome"},
            headers={"X-Device-Id": str(device)},
        )

    def with_cookie(self, path: str, device: DeviceId, refresh_token: str) -> httpx.Response:
        """Rejoue un cookie précis (le pot du client est vidé pour ne rien envoyer d'autre)."""
        self.client.cookies.clear()
        return self.client.post(
            f"{PREFIX}{path}",
            headers={"X-Device-Id": str(device), "Cookie": f"refresh_token={refresh_token}"},
        )

    def get(self, path: str, device: DeviceId, access_token: str) -> httpx.Response:
        return self.client.get(
            f"{PREFIX}{path}",
            headers={"X-Device-Id": str(device), "Authorization": f"Bearer {access_token}"},
        )
