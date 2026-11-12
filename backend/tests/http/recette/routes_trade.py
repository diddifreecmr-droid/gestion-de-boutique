"""Routes de boutique (suite) : achats, ventes, créances, tableau de bord, hors-ligne."""

from collections.abc import Mapping
from typing import Any

from app.domain.shared.ids import DeviceId
from tests.http.recette.paths import Body, phone, unique, versioned
from tests.http.recette.world import SENTINEL_COST, SENTINEL_PRICE, Side


def _purchase(side: Side) -> dict[str, Any]:
    line = {"article_id": side.ids["article"], "quantity": "1", "unit_price": SENTINEL_COST}
    return {"lines": [line], "location_id": side.ids["garoua"]}


def cash_sale(side: Side, price: int = SENTINEL_PRICE) -> dict[str, Any]:
    return {
        "kind": "cash",
        "lines": [{"article_id": side.ids["article"], "quantity": "1", "unit_price": price}],
        "payments": [{"mode_id": side.ids["cash"], "amount": price}],
    }


def _pay(side: Side) -> dict[str, Any]:
    return {"amount": 1_000, "mode_id": side.ids["cash"]}


def _legacy(side: Side) -> dict[str, Any]:
    return {
        "customer": {"name": unique("Client"), "phone": phone()},
        "amount": 300_000,
        "opened_on": "2026-03-01",
        "description": "cahier 2026",
    }


def _sheet_version(path: str, key: str, nested: str) -> Body:
    """Fiche qui emboîte l'objet (client, fournisseur) : version lue dans `nested`."""

    def body(side: Side) -> dict[str, Any]:
        sheet = side.ok("GET", f"{path}/{side.ids[key]}", side.owner)
        return {"version": int(sheet[nested]["version"]), "city": "Garoua"}

    return body


TRADE_ROUTES: Mapping[str, Body | None] = {
    "GET /suppliers": None,
    "POST /suppliers": lambda s: {"name": unique("Fournisseur")},
    "GET /suppliers/{supplier_id}": None,
    "PATCH /suppliers/{supplier_id}": _sheet_version("/suppliers", "supplier", "supplier"),
    "GET /purchases": None,
    "POST /purchases": _purchase,
    "GET /purchases/{purchase_id}": None,
    "PATCH /purchases/{purchase_id}": versioned("/purchases/{purchase_id}", reason="note",
                                                note="vu"),
    "POST /purchases/{purchase_id}/cancel": lambda s: {"reason": "doublon"},
    "POST /purchases/{purchase_id}/payments": _pay,
    "GET /sales": None,
    "POST /sales": cash_sale,
    "GET /sales/{sale_id}": None,
    "PATCH /sales/{sale_id}": versioned("/sales/{sale_id}", reason="note", note="vu"),
    "POST /sales/{sale_id}/cancel": lambda s: {"reason": "client a renoncé"},
    "POST /sales/{sale_id}/error-reports": lambda s: {"description": "mauvais prix"},
    "POST /error-reports/{report_id}/reply": lambda s: {"reply": "corrigé"},
    "GET /sales/{sale_id}/receipt": None,
    "GET /customers": None,
    "POST /customers": lambda s: {"name": unique("Awa"), "phone": phone()},
    "GET /customers/{customer_id}": None,
    "PATCH /customers/{customer_id}": _sheet_version("/customers", "customer_seller", "customer"),
    "POST /price-requests": lambda s: {"article_id": s.ids["article"],
                                       "requested_price": 700_000},
    "GET /price-requests": None,
    "GET /price-requests/{request_id}": None,
    "POST /price-requests/{request_id}/decision": lambda s: {"decision": "refuse"},
    "POST /sales/{sale_id}/returns": lambda s: {
        "lines": [{"line": 1, "quantity": "1", "chassis": ["LBX123"]}], "reason": "défaut"},
    "GET /sales/{sale_id}/returns": None,
    "GET /receivables": None,
    "POST /receivables": _legacy,
    "GET /receivables/{receivable_id}": None,
    "PATCH /receivables/{receivable_id}": versioned("/receivables/{receivable_id}", terms="ok"),
    "POST /receivables/{receivable_id}/write-off": lambda s: {"reason": "client parti"},
    "POST /receivables/{receivable_id}/reminders": lambda s: {"remind_on": "2027-01-15"},
    "PATCH /reminders/{reminder_id}": lambda s: {"status": "done"},
    "POST /receivables/{receivable_id}/guarantors": lambda s: {"name": "Issa", "phone": phone()},
    "POST /receivables/{receivable_id}/installments": _pay,
    "POST /customers/{customer_id}/installments": _pay,
    "POST /installments/{installment_id}/cancel": lambda s: {"reason": "chèque sans provision"},
    "GET /installments/{installment_id}/receipt": None,
    "GET /customers/{customer_id}/statement": None,
    "GET /dashboard": None,
    "GET /dashboard/details/{metric}": None,
    "GET /home": None,
    "POST /sync": lambda s: {"device_id": str(DeviceId.new()), "operations": []},
    "GET /offline-snapshot": None,
}  # fmt: skip
