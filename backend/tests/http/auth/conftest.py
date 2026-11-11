"""Fixture `api` : application assemblée par la composition root (horloge figée, Argon2 allégé).

Une route de sonde `/shops/{shop_id}/probe` exerce la dépendance `current_actor`.
"""

from collections.abc import Iterator
from typing import Annotated

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from app.application.security.actor import Actor
from app.bootstrap.config import Settings
from app.bootstrap.container import http_config_from
from app.bootstrap.identity import build_identity
from app.infrastructure.auth.argon2_hasher import Argon2PasswordHasher
from app.infrastructure.persistence.memory.clock import FixedClock
from app.interface.http.app import create_app
from tests.application.identity.support import T0
from tests.http.auth.support import PREFIX, Api


@pytest.fixture
def api(settings: Settings) -> Iterator[Api]:
    clock = FixedClock(T0)
    hasher = Argon2PasswordHasher(time_cost=1, memory_cost_kib=8, parallelism=1)
    module = build_identity(settings, clock=clock, hasher=hasher)
    app = create_app(http_config_from(settings), module.auth)

    @app.get(f"{PREFIX}/shops/{{shop_id}}/probe")
    def probe(actor: Annotated[Actor, Depends(module.auth.guard.current_actor)]) -> dict[str, str]:
        return {"role": actor.role.value if actor.role else "platform_admin"}

    with TestClient(app, base_url="https://testserver", raise_server_exceptions=False) as client:
        yield Api(client, module, clock)
