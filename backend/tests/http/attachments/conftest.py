"""Application complète (socle, catalogue, stock, achats, ventes, créances, dépenses, journal,
pièces jointes) en mémoire : horloge figée déplaçable, stockage mémoire observable."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Protocol

import httpx2 as httpx
import pytest
from fastapi.testclient import TestClient

from app.application.attachments.ports import FileStorage
from app.bootstrap.attachments import build_attachments
from app.bootstrap.catalog import build_catalog
from app.bootstrap.config import Settings
from app.bootstrap.container import http_config_from
from app.bootstrap.core import build_core
from app.bootstrap.expenses import build_expenses
from app.bootstrap.identity import build_identity
from app.bootstrap.journal import build_journal
from app.bootstrap.purchasing import build_purchasing
from app.bootstrap.receivables import build_receivables
from app.bootstrap.sales import build_sales, sales_ranking
from app.bootstrap.shops import build_shops
from app.bootstrap.stock import build_stock
from app.domain.identity.phone import PhoneNumber
from app.domain.identity.user import User
from app.infrastructure.persistence.memory.clock import FixedClock
from app.infrastructure.storage.memory import MemoryFileStorage
from app.interface.http.app import create_app
from tests.application.identity.support import PASSWORD, T0, FakeHasher
from tests.application.shops.support import FixedPins
from tests.contracts.storage import file_storage, storage_prefix
from tests.http.catalog.test_catalog_http import Shop
from tests.http.shops.conftest import ADMIN_PHONE, Api, Session

__all__ = ["file_storage", "storage_prefix"]  # fixtures du banc de contrat (stockage)

JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + bytes(range(256)) * 8
GIF = b"GIF89a" + b"\x00" * 64


class ShopLike(Protocol):
    def call(self, method: str, suffix: str, who: Session, **kwargs: Any) -> Any: ...


@dataclass
class Bench[StorageT: FileStorage]:
    api: Api
    clock: FixedClock
    storage: StorageT

    def upload(
        self, shop: ShopLike, who: Session, content: bytes = JPEG, /, **fields: str
    ) -> httpx.Response:
        files = {"file": ("photo.jpg", content, "image/jpeg")}
        sent: httpx.Response = shop.call("POST", "/attachments", who, files=files, data=fields)
        return sent

    def link(self, shop: ShopLike, who: Session, attachment_id: str) -> httpx.Response:
        sent: httpx.Response = shop.call("GET", f"/attachments/{attachment_id}/url", who)
        return sent

    def open(self, url: str) -> httpx.Response:
        """Le navigateur ouvre le lien : aucun jeton, aucun en-tête d'appareil."""
        return self.api.client.get(url)


type MemoryBench = Bench[MemoryFileStorage]


def add_seller(shop: Shop, phone: str) -> Session:
    locations = shop.call("GET", "/locations", shop.owner).json()["items"]
    garoua = next(loc["id"] for loc in locations if loc["name"] == "Garoua")
    body: dict[str, Any] = {
        "name": "Vendeur 2",
        "phone": phone,
        "role": "seller",
        "default_location_id": garoua,
    }
    added = shop.call("POST", "/members", shop.owner, json=body)
    assert added.status_code == 201, added.text
    return shop.api.login(phone, added.json()["temporary_pin"])


@contextmanager
def assembled[StorageT: FileStorage](
    settings: Settings, storage: StorageT
) -> Iterator[Bench[StorageT]]:
    clock = FixedClock(T0)
    hasher = FakeHasher()
    core = build_core(settings, clock)
    identity = build_identity(settings, hasher=hasher, core=core)
    journal = build_journal(settings, clock=clock, guard=identity.auth.guard, core=core)
    stock = build_stock(identity)
    app = create_app(
        http_config_from(settings),
        identity.auth,
        journal.http,
        build_shops(identity, pins=FixedPins()).http,
        catalog=build_catalog(identity, ranking=sales_ranking(clock)).http,
        expenses=build_expenses(identity).http,
        stock=stock.http,
        purchasing=build_purchasing(identity, stock.ledger).http,
        sales=build_sales(identity, stock.ledger).http,
        receivables=build_receivables(identity).http,
        attachments=build_attachments(settings, identity, storage).http,
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
        yield Bench(Api(client, identity), clock, storage)


@pytest.fixture
def bench(settings: Settings) -> Iterator[MemoryBench]:
    """Stockage mémoire observable (panne simulée, clés écrites)."""
    with assembled(settings, MemoryFileStorage()) as built:
        yield built


@pytest.fixture
def live_bench(settings: Settings, file_storage: FileStorage) -> Iterator[Bench[FileStorage]]:
    """Stockage du banc de contrat : mémoire, ou Silo de dev avec `--storage=s3`."""
    with assembled(settings, file_storage) as built:
        yield built


@pytest.fixture
def api(bench: MemoryBench) -> Api:
    """Pour les aides des autres bancs (`sold`, `Shop`) qui attendent la fixture `api`."""
    return bench.api
