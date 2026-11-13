"""Application avec le socle, le catalogue, les pièces jointes et l'import (modèles témoins),
stockage mémoire observable.

Le module `import` est **à venir** jusqu'à T46 : `importable` le rend activable pour la durée
d'un test (retrait de `UPCOMING_MODULES`, lu à chaque contrôle) puis l'active pour la
boutique ; sans cette fixture, toutes les routes de l'import répondent 403 `MODULE_DISABLED`.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.application.imports.models import ImportModel
from app.bootstrap.attachments import build_attachments
from app.bootstrap.catalog import build_catalog
from app.bootstrap.config import Settings
from app.bootstrap.container import http_config_from
from app.bootstrap.core import build_core
from app.bootstrap.identity import build_identity
from app.bootstrap.imports import build_imports
from app.bootstrap.journal import build_journal
from app.bootstrap.sales import sales_ranking
from app.bootstrap.shops import build_shops
from app.domain.identity.phone import PhoneNumber
from app.domain.identity.user import User
from app.domain.profiles import modules as profile_modules
from app.domain.profiles.modules import AVAILABLE_MODULES, Module
from app.infrastructure.persistence.memory.clock import FixedClock
from app.infrastructure.storage.memory import MemoryFileStorage
from app.interface.http.app import create_app
from tests.application.identity.support import PASSWORD, T0, FakeHasher
from tests.application.imports.support import WITNESSES
from tests.application.shops.support import FixedPins
from tests.http.catalog.test_catalog_http import Shop
from tests.http.shops.conftest import ADMIN_PHONE, Api, Session


@dataclass
class Bench:
    api: Api
    storage: MemoryFileStorage

    def preview(self, shop: Shop, who: Session, content: bytes, kind: str = "articles") -> Any:
        files = {"file": ("articles.csv", content, "text/csv")}
        return shop.call("POST", "/imports/preview", who, files=files, data={"kind": kind})

    def confirm(self, shop: Shop, who: Session, preview_id: str) -> Any:
        return shop.call("POST", "/imports", who, json={"preview_id": preview_id})


@pytest.fixture
def bench_models() -> tuple[ImportModel, ...] | None:
    """Modèles branchés : les témoins ; un module de test le redéfinit à `None` (registre réel)."""
    return WITNESSES


@pytest.fixture
def bench(settings: Settings, bench_models: tuple[ImportModel, ...] | None) -> Iterator[Bench]:
    clock = FixedClock(T0)
    hasher = FakeHasher()
    core = build_core(settings, clock)
    identity = build_identity(settings, hasher=hasher, core=core)
    journal = build_journal(settings, clock=clock, guard=identity.auth.guard, core=core)
    storage = MemoryFileStorage()
    attachments = build_attachments(settings, identity, storage)
    app = create_app(
        http_config_from(settings),
        identity.auth,
        journal.http,
        build_shops(identity, pins=FixedPins()).http,
        catalog=build_catalog(identity, ranking=sales_ranking(clock)).http,
        attachments=attachments.http,
        imports=build_imports(identity, attachments.storage, bench_models).http,
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
        yield Bench(Api(client, identity), storage)


@pytest.fixture
def shop(bench: Bench) -> Shop:
    return Shop(bench.api)


@pytest.fixture
def importable(bench: Bench, shop: Shop, monkeypatch: pytest.MonkeyPatch) -> Shop:
    """La boutique avec le module `import` actif (comme après T46)."""
    upcoming = profile_modules.UPCOMING_MODULES - {Module.IMPORT}
    monkeypatch.setattr(profile_modules, "UPCOMING_MODULES", upcoming)
    body = {"modules": sorted({*AVAILABLE_MODULES, Module.IMPORT})}
    admin = bench.api.admin()
    response = bench.api.call("PATCH", f"/platform/shops/{shop.id}", admin, json=body)
    assert response.status_code == 200, response.text
    return shop
