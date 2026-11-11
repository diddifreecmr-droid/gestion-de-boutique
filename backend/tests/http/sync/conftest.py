"""Application complète (Lot 1 + ossature hors connexion T23) en mémoire, horloge figée.

`desk` : « Motos Garoua » ouverte (propriétaire, vendeur, comptable, chauffeur), un article
« Haojue HJ125-8 » sans stock (une vente différée rend le stock négatif, RG-T18) et des
outils pour composer les opérations de `POST /sync`. Le droit `offline_capture` est **faux**
au départ (V1) ; `desk.enable()` le pose comme l'administrateur (surcharge, ERR-FEA-04).
"""

from collections.abc import Iterator
from dataclasses import dataclass, field
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
from app.bootstrap.sales import build_sales, sales_ranking
from app.bootstrap.shops import build_shops
from app.bootstrap.stock import build_stock
from app.bootstrap.sync import build_sync
from app.domain.identity.phone import PhoneNumber
from app.domain.identity.user import User
from app.domain.shared.doc_number import DocType, ProvisionalDocNumber
from app.domain.sync.operation import SyncOperationId
from app.infrastructure.persistence.memory.clock import FixedClock
from app.interface.http.app import create_app
from tests.application.identity.support import PASSWORD, T0, FakeHasher
from tests.application.shops.support import FixedPins
from tests.http.catalog.test_catalog_http import HJ, Shop
from tests.http.sales.test_sales_returns_http import minimum
from tests.http.shops.conftest import ADMIN_PHONE, Api, Session

CAPTURED = "2026-11-10T09:00:00+01:00"


@dataclass
class Desk:
    api: Api
    shop: Shop = field(init=False)
    article: dict[str, Any] = field(init=False)

    def __post_init__(self) -> None:
        self.shop = Shop(self.api)
        self.article = self.ok("POST", "/articles", self.shop.owner, json=HJ)
        minimum(self.shop, self.article)  # base 780 000, minimum 720 000, réglage actif

    def staff(self, role: str) -> Session:
        return self.shop.staff[role]

    def call(self, method: str, suffix: str, who: Session, **kwargs: Any) -> Any:
        return self.shop.call(method, suffix, who, **kwargs)

    def ok(self, method: str, suffix: str, who: Session, **kwargs: Any) -> Any:
        response = self.call(method, suffix, who, **kwargs)
        assert response.status_code in (200, 201), response.text
        return response.json()

    def enable(self, enabled: bool | None = True) -> None:
        patch = {"entitlements": {"offline_capture": enabled}}
        response = self.api.call("PATCH", f"/platform/shops/{self.shop.id}", self.api.admin(),
                                 json=patch)  # fmt: skip
        assert response.status_code == 200, response.text

    def mode(self, name: str = "Espèces") -> str:
        modes = self.ok("GET", "/payment-modes", self.shop.owner)
        return str(next(m["id"] for m in modes if m["name"] == name))

    def category(self, name: str) -> str:
        found = self.ok("GET", "/expense-categories", self.shop.owner)
        return str(next(c["id"] for c in found if c["name"] == name))

    def sale_payload(self, price: int = 780_000) -> dict[str, Any]:
        return {
            "kind": "cash",
            "lines": [{"article_id": self.article["id"], "quantity": "1", "unit_price": price}],
            "payments": [{"mode_id": self.mode(), "amount": price}],
        }

    def op(self, who: Session, seq: int, payload: dict[str, Any], *, kind: str = "sale.create",
           doc: DocType = DocType.SALE, op_id: str | None = None) -> dict[str, Any]:  # fmt: skip
        return {
            "op_id": op_id or str(SyncOperationId.new()),
            "type": kind,
            "provisional_number": str(ProvisionalDocNumber.for_device(doc, who.device, seq)),
            "captured_at": CAPTURED,
            "payload": payload,
        }

    def sync(self, who: Session, *operations: dict[str, Any]) -> Any:
        body = {"device_id": str(who.device), "operations": list(operations)}
        return self.call("POST", "/sync", who, json=body)

    def results(self, who: Session, *operations: dict[str, Any]) -> list[dict[str, Any]]:
        response = self.sync(who, *operations)
        assert response.status_code == 200, response.text
        assert response.headers["Cache-Control"] == "no-store"
        found: list[dict[str, Any]] = response.json()["results"]
        return found

    def alerts(self, who: Session, kind: str) -> list[dict[str, Any]]:
        items = self.ok("GET", "/alerts", who)["items"]
        return [a for a in items if a["type"] == kind]


@pytest.fixture
def desk(settings: Settings) -> Iterator[Desk]:
    clock = FixedClock(T0)
    hasher = FakeHasher()
    core = build_core(settings, clock)
    identity = build_identity(settings, hasher=hasher, core=core)
    journal = build_journal(settings, clock=clock, guard=identity.auth.guard, core=core)
    shops = build_shops(identity, pins=FixedPins())
    stock = build_stock(identity)
    sales = build_sales(identity, stock.ledger)
    expenses = build_expenses(identity)
    app = create_app(
        http_config_from(settings),
        identity.auth,
        journal.http,
        shops.http,
        catalog=build_catalog(identity, ranking=sales_ranking(clock)).http,
        expenses=expenses.http,
        stock=stock.http,
        purchasing=build_purchasing(identity, stock.ledger).http,
        sales=sales.http,
        sync=build_sync(identity, journal, sales, expenses).http,
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
        yield Desk(Api(client, identity))
