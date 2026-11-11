"""Application HTTP avec limitation de débit **activée** (seuils par défaut), horloge figée.

`RateLimitedApi.client_from(ip)` simule une connexion TCP depuis `ip` (même application, donc
mêmes compteurs) ; `X-Forwarded-For` se passe en en-tête.
"""

from dataclasses import dataclass, field
from ipaddress import ip_network

import httpx2 as httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.bootstrap.config import Environment, Settings
from app.bootstrap.container import http_config_from
from app.bootstrap.identity import build_identity
from app.infrastructure.auth.argon2_hasher import Argon2PasswordHasher
from app.infrastructure.persistence.memory.clock import FixedClock
from app.interface.http.app import create_app
from tests.application.identity.support import PIN, T0

PREFIX = "/api/v1"
DEVICE = "019a7d1e-5c4b-7a00-8000-000000000001"


@dataclass
class RateLimitedApi:
    app: FastAPI
    clock: FixedClock
    _clients: dict[str, TestClient] = field(default_factory=dict)

    def client_from(self, ip: str) -> TestClient:
        if ip not in self._clients:
            self._clients[ip] = TestClient(
                self.app,
                base_url="https://testserver",
                raise_server_exceptions=False,
                client=(ip, 50000),
            )
        return self._clients[ip]

    def login(
        self, ip: str, phone: str = "677001122", forwarded_for: str | None = None
    ) -> httpx.Response:
        headers = {"X-Device-Id": DEVICE}
        if forwarded_for is not None:
            headers["X-Forwarded-For"] = forwarded_for
        return self.client_from(ip).post(
            f"{PREFIX}/auth/login",
            json={"phone": phone, "pin": PIN, "device_label": "PC"},
            headers=headers,
        )

    def post(self, ip: str, path: str) -> httpx.Response:
        return self.client_from(ip).post(f"{PREFIX}{path}", headers={"X-Device-Id": DEVICE})


def build_api(trusted_proxies: str = "") -> RateLimitedApi:
    settings = Settings(
        ENVIRONMENT=Environment.TEST,
        AUTH_RATE_LIMIT_ENABLED=True,
        AUTH_TRUSTED_PROXIES=tuple(ip_network(p) for p in trusted_proxies.split(",") if p),
        _env_file=None,
    )
    clock = FixedClock(T0)
    hasher = Argon2PasswordHasher(time_cost=1, memory_cost_kib=8, parallelism=1)
    module = build_identity(settings, clock=clock, hasher=hasher)
    return RateLimitedApi(create_app(http_config_from(settings), module.auth), clock)
