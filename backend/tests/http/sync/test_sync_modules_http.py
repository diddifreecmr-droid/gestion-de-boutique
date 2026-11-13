"""Saisie hors connexion et modules éteints (specs § 15.1) : `POST /sync` est du socle, mais
chaque opération rejouée passe par le cas d'utilisation en ligne, qui refuse l'effet d'un
module désactivé (`MODULE_DISABLED`, opération `rejected`, rien d'écrit)."""

from typing import Any

from app.domain.profiles.modules import ALL_MODULES, Module
from app.domain.shared.doc_number import DocType
from tests.http.sync.conftest import Desk


def _modules(desk: Desk, *off: Module) -> None:
    wanted = sorted(m.value for m in ALL_MODULES - set(off))
    response = desk.api.call(
        "PATCH", f"/platform/shops/{desk.shop.id}", desk.api.admin(), json={"modules": wanted}
    )
    assert response.status_code == 200, response.text


def _credit(desk: Desk) -> dict[str, Any]:
    return {
        **desk.sale_payload(),
        "kind": "credit",
        "customer": {"name": "Awa", "phone": "+237690000077", "kind": "individual"},
        "payments": [],
    }


def test_offline_expense_without_the_expenses_module_is_rejected(desk: Desk) -> None:
    desk.enable()
    accountant = desk.staff("accountant")
    expense = {"amount": 5_000, "category_id": desk.category("Carburant")}
    _modules(desk, Module.EXPENSES)
    [result] = desk.results(
        accountant, desk.op(accountant, 1, expense, kind="expense.create", doc=DocType.EXPENSE)
    )
    assert result["status"] == "rejected"
    assert result["error"]["code"] == "MODULE_DISABLED"
    assert result["error"]["details"] == {"module": "expenses"}
    _modules(desk)  # réactivé : aucune dépense n'a été écrite
    assert desk.ok("GET", "/expenses", desk.shop.owner)["items"] == []


def test_offline_credit_sale_without_receivables_is_rejected_cash_is_accepted(
    desk: Desk,
) -> None:
    desk.enable()
    _modules(desk, Module.RECEIVABLES)
    seller = desk.staff("seller")
    credit, cash = desk.op(seller, 1, _credit(desk)), desk.op(seller, 2, desk.sale_payload())
    results = desk.results(seller, credit, cash)
    assert results[0]["status"] == "rejected"
    assert results[0]["error"] == {
        "code": "MODULE_DISABLED",
        "message": results[0]["error"]["message"],
        "details": {"module": "receivables"},
    }
    assert results[1]["status"] == "accepted"
