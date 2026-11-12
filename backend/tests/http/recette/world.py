"""Jeu de recette (docs/recette-lot1.md § 3) : boutiques A et B remplies par l'API publique.

Chaque boutique : propriétaire, vendeurs V et V2 (lieu habituel Garoua), comptable C, chauffeur
CH ; article « Haojue HJ125-8 » (prix de base 780 000, minimum 720 000, réglage actif sans
accord) ; achat de 20 motos par C au **coût sentinelle 543 210** ; vente à crédit de V et de
V2 au **prix sentinelle 777 777** (créances ouvertes) ; versement de V ; dépense de C.
L'utilisateur **U** est vendeur dans A et comptable dans B (SEC-I07).
"""

from dataclasses import dataclass, field
from typing import Any

import httpx2 as httpx

from app.domain.sales.ids import SaleId
from tests.http.shops.conftest import NEW_PIN, Api, Session

SENTINEL_COST = 543_210
SENTINEL_PRICE = 777_777
HJ = {"fields": {"brand": "Haojue", "model": "HJ125-8", "engine_cc": 125}}
ROLES = ("seller", "seller2", "accountant", "driver")


@dataclass
class Side:
    """Une boutique du jeu : sessions par rôle (`owner`, `seller`, …) et identifiants utiles."""

    api: Api
    id: str
    sessions: dict[str, Session] = field(default_factory=dict)
    users: dict[str, str] = field(default_factory=dict)
    ids: dict[str, str] = field(default_factory=dict)

    @property
    def owner(self) -> Session:
        return self.sessions["owner"]

    def call(self, method: str, suffix: str, who: Session, **kwargs: Any) -> httpx.Response:
        return self.api.call(method, f"/shops/{self.id}{suffix}", who, **kwargs)

    def ok(self, method: str, suffix: str, who: Session, **kwargs: Any) -> Any:
        response = self.call(method, suffix, who, **kwargs)
        assert response.status_code in (200, 201), f"{method} {suffix} : {response.text}"
        return response.json()

    def version(self, suffix: str) -> int:
        return int(self.ok("GET", suffix, self.owner)["version"])

    def add_member(self, role: str, phone: str, name: str) -> dict[str, Any]:
        body: dict[str, Any] = {"name": name, "phone": phone, "role": role.rstrip("2")}
        if role.startswith("seller"):
            body["default_location_id"] = self.ids["garoua"]
        added: dict[str, Any] = self.ok("POST", "/members", self.owner, json=body)
        return added

    def credit_sale(self, who: Session, name: str, phone: str, chassis: str, deposit: int) -> Any:
        body = {
            "id": str(SaleId.new()),
            "kind": "credit",
            "customer": {"name": name, "phone": phone, "kind": "individual"},
            "lines": [{"article_id": self.ids["article"], "quantity": "1",
                       "unit_price": SENTINEL_PRICE, "details": [{"chassis_number": chassis}]}],
            "payments": [{"mode_id": self.ids["cash"], "amount": deposit}] if deposit else [],
            "credit": {"reminder_on": "2026-12-01"},
        }  # fmt: skip
        return self.ok("POST", "/sales", who, json=body)


def _open(api: Api, admin: Session, name: str, owner_phone: str, staff_prefix: str) -> Side:
    opened = api.call("POST", "/platform/shops", admin, json={
        "profile_code": "motos", "name": name, "city": "Garoua", "phone": "222000000",
        "owner": {"name": f"Propriétaire {name}", "phone": owner_phone},
    }).json()  # fmt: skip
    side = Side(api, opened["shop"]["shop_id"])
    side.sessions["owner"] = api.login(owner_phone, opened["temporary_pin"])
    places = side.ok("GET", "/locations", side.owner)["items"]
    side.ids.update({p["name"].lower(): p["id"] for p in places})
    for index, role in enumerate(ROLES):
        phone = f"{staff_prefix}{index:02d}"
        added = side.add_member(role, phone, f"{role} {name}")
        side.users[role] = added["member"]["user_id"]
        side.sessions[role] = api.login(phone, added["temporary_pin"])
    return side


def _seed(side: Side) -> None:
    owner, accountant = side.owner, side.sessions["accountant"]
    article = side.ok("POST", "/articles", owner, json={**HJ, "base_price": 780_000})
    side.ids["article"] = article["id"]
    settings = side.ok("GET", "/settings", owner)
    side.ok("PATCH", "/settings", owner,
            json={"version": settings["version"], "min_price_enabled": True})  # fmt: skip
    side.ok("PUT", f"/articles/{article['id']}/prices", owner,
            json={"version": side.version(f"/articles/{article['id']}"), "min_price": 720_000})  # fmt: skip
    modes = side.ok("GET", "/payment-modes", owner)
    side.ids["cash"] = next(m["id"] for m in modes if m["name"] == "Espèces")
    categories = side.ok("GET", "/expense-categories", owner)
    side.ids["fuel"] = next(c["id"] for c in categories if c["name"] == "Carburant")
    side.ids["supplier"] = side.ok("POST", "/suppliers", accountant, json={"name": "Haojue SA"})["id"]
    purchase = side.ok("POST", "/purchases", accountant, json={
        "lines": [{"article_id": article["id"], "quantity": "20", "unit_price": SENTINEL_COST}],
        "supplier_id": side.ids["supplier"], "location_id": side.ids["garoua"],
    })  # fmt: skip
    side.ids["purchase"] = purchase["id"]
    for who, name, phone, chassis, deposit in (
        ("seller", "Moussa A.", "+237690000000", "LBX123", 300_000),
        ("seller2", "Ali B.", "+237690000099", "LBX124", 0),
    ):
        sale = side.credit_sale(side.sessions[who], name, phone, chassis, deposit)
        side.ids[f"sale_{who}"] = sale["id"]
        side.ids[f"receivable_{who}"] = sale["receivable"]["id"]
        side.ids[f"customer_{who}"] = sale["customer_id"]
    paid = side.ok("POST", f"/receivables/{side.ids['receivable_seller']}/installments",
                   side.sessions["seller"], json={"amount": 100_000, "mode_id": side.ids["cash"]})  # fmt: skip
    side.ids["installment"] = paid["installment"]["id"]
    expense = side.ok("POST", "/expenses", accountant,
                      json={"amount": 25_000, "category_id": side.ids["fuel"], "tags": ["groupe"]})  # fmt: skip
    side.ids["expense"] = expense["id"]
    _extras(side)


def _extras(side: Side) -> None:
    """Objets visés par les routes à identifiant : inventaire, signalement, demande de prix…"""
    owner, seller = side.owner, side.sessions["seller"]
    inventory = side.ok("POST", "/inventories", side.sessions["accountant"],
                        json={"location_id": side.ids["ngaoundéré"]})  # fmt: skip
    side.ids["inventory"] = inventory["id"]
    sale = side.ids["sale_seller"]
    report = side.ok("POST", f"/sales/{sale}/error-reports", seller, json={"description": "prix"})
    side.ids["report"] = report["id"]
    receivable = side.ok("GET", f"/receivables/{side.ids['receivable_seller']}", owner)
    side.ids["reminder"] = receivable["reminders"][0]["id"]
    side.ids["alert"] = side.ok("GET", "/alerts", owner)["items"][0]["id"]
    side.ok("POST", "/expenses", owner, json={"amount": 1_000, "category_id": side.ids["fuel"],
                                              "tags": ["groupe électrogène"]})  # fmt: skip
    tags = {t["name"]: t["id"] for t in _items(side.ok("GET", "/tags", owner))}
    side.ids["tag"], side.ids["tag2"] = tags["groupe"], tags["groupe électrogène"]
    approval(side, True)
    request = side.ok("POST", "/price-requests", seller,
                      json={"article_id": side.ids["article"], "requested_price": 700_000})  # fmt: skip
    side.ids["price_request"] = request["id"]
    approval(side, False)


def _items(found: Any) -> list[dict[str, Any]]:
    return list(found["items"] if isinstance(found, dict) else found)


def approval(side: Side, required: bool) -> None:
    """Réglage « Accord du propriétaire sous le prix minimum » (désactivé par défaut)."""
    version = side.version("/settings")
    side.ok("PATCH", "/settings", side.owner,
            json={"version": version, "min_price_requires_approval": required})  # fmt: skip


@dataclass
class World:
    api: Api
    a: Side
    b: Side
    admin: Session
    u: Session  # vendeur dans A, comptable dans B

    @classmethod
    def build(cls, api: Api) -> "World":
        admin = api.admin()
        a = _open(api, admin, "Motos Garoua", "690000001", "6770000")
        b = _open(api, admin, "Motos Ngaoundéré", "690000101", "6771000")
        _seed(a)
        _seed(b)
        u_phone = "677999999"
        first = a.add_member("seller", u_phone, "U")
        u = api.login(u_phone, first["temporary_pin"])
        b.add_member("accountant", u_phone, "U")
        return cls(api, a, b, admin, u)

    def relogin(self, phone: str) -> Session:
        return self.api.login(phone, NEW_PIN)
