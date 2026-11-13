"""Jeu de la recette du Lot 3 (`docs/recette-lot3.md` § 0) sur l'application complète en mémoire.

- Boutique **P** « Mode Garoua » (Prêt-à-porter) : **O**, **E** (employé = rôle `seller`),
  **C** (comptable). Articles **CH** « Chemise lin » et **RB** « Robe pagne ».
- Boutique **X** « Tissus Ngaoundéré » (Textile) : article **WX** « Wax Fleur de mariage »,
  unité Mètre, vente à la pièce, pièce 5,49 m, base 2 500 /m et 13 000 /pièce.
- Boutique **B** : autre commerçant, Prêt-à-porter, propriétaire **OB** seul (isolation).

Les ouvertures passent par `POST /platform/shops` (profil du code demandé), les membres par
`POST /members` : aucun raccourci de base, tout passe par les routes publiques.
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

import httpx2 as httpx

from app.domain.purchasing.ids import PurchaseId
from app.domain.sales.ids import SaleId
from tests.http.attachments.conftest import Bench
from tests.http.shops.conftest import Session

WX_FIELDS = {
    "name": "Wax Fleur de mariage",
    "unit": "METER",
    "sold_by_piece": True,
    "piece_length_m": "5.49",
}
WX_PRICES = {"base_price": 2_500, "base_price_piece": 13_000}


class Lot3Shop:
    def __init__(
        self,
        bench: Bench[Any],
        profile_code: str,
        name: str,
        owner_phone: str,
        staff: dict[str, str] | None = None,
    ) -> None:
        self.bench, self.api = bench, bench.api
        body = {
            "profile_code": profile_code,
            "name": name,
            "city": "Garoua",
            "phone": "222000000",
            "owner": {"name": "Awa", "phone": owner_phone},
        }
        opened = self.api.call("POST", "/platform/shops", self.api.admin(), json=body)
        assert opened.status_code == 201, opened.text
        self.id = opened.json()["shop"]["shop_id"]
        self.owner = self.api.login(owner_phone, opened.json()["temporary_pin"])
        self.store = self._store()
        self.staff: dict[str, Session] = {}
        for role, phone in (staff or {}).items():
            member = {"name": role, "phone": phone, "role": role}
            if role == "seller":
                member["default_location_id"] = self.store
            added = self.call("POST", "/members", self.owner, json=member)
            assert added.status_code == 201, added.text
            self.staff[role] = self.api.login(phone, added.json()["temporary_pin"])

    def _store(self) -> str:
        locations = self.call("GET", "/locations", self.owner).json()["items"]
        return str(next(loc["id"] for loc in locations if loc["name"] == "Boutique"))

    def call(self, method: str, suffix: str, who: Session, **kwargs: Any) -> httpx.Response:
        return self.api.call(method, f"/shops/{self.id}{suffix}", who, **kwargs)

    def settings(self, **values: Any) -> dict[str, Any]:
        version = self.call("GET", "/settings", self.owner).json()["version"]
        patched = self.call("PATCH", "/settings", self.owner, json={"version": version, **values})
        assert patched.status_code == 200, patched.text
        result: dict[str, Any] = patched.json()
        return result

    def article(self, fields: dict[str, Any], **prices: int) -> dict[str, Any]:
        created = self.call("POST", "/articles", self.owner, json={"fields": fields, **prices})
        assert created.status_code == 201, created.text
        result: dict[str, Any] = created.json()
        return result

    def buy(
        self, article: dict[str, Any], quantity: str, price: int, unit: str | None = None
    ) -> dict[str, Any]:
        line: dict[str, Any] = {"article_id": article["id"], "quantity": quantity}
        line |= {"unit_price": price} | ({} if unit is None else {"unit": unit})
        body = {"id": str(PurchaseId.new()), "lines": [line]}
        bought = self.call("POST", "/purchases", self.owner, json=body)
        assert bought.status_code == 201, bought.text
        result: dict[str, Any] = bought.json()
        return result

    def cash_mode(self) -> str:
        modes = self.call("GET", "/payment-modes", self.owner).json()
        return str(next(m["id"] for m in modes if m["name"] == "Espèces"))

    def sell(self, who: Session, *lines: dict[str, Any]) -> httpx.Response:
        total = sum(_line_total(line) for line in lines)
        payments = [{"mode_id": self.cash_mode(), "amount": total}] if total else []
        body = {"id": str(SaleId.new()), "kind": "cash", "lines": list(lines), "payments": payments}
        return self.call("POST", "/sales", who, json=body)


def _line_total(line: dict[str, Any]) -> int:
    total = Decimal(line["quantity"]) * line["unit_price"]
    return int(total.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def apparel_shop(bench: Bench[Any]) -> Lot3Shop:
    staff = {"seller": "677100002", "accountant": "677100003"}
    return Lot3Shop(bench, "apparel", "Mode Garoua", "690100001", staff)


def textile_shop(bench: Bench[Any]) -> Lot3Shop:
    staff = {"seller": "677200002", "accountant": "677200003"}
    return Lot3Shop(bench, "textile", "Tissus Ngaoundéré", "690200001", staff)


def other_shop(bench: Bench[Any]) -> Lot3Shop:
    return Lot3Shop(bench, "apparel", "Boutique B", "690300001")


def keys_of(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in keys_of(v)}
    if isinstance(value, list):
        return {k for item in value for k in keys_of(item)}
    return set()
