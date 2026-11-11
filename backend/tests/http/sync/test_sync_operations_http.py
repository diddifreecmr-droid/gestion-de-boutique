"""`POST /sync` avec le droit activé (configuration de test) : idempotence (OFF-05), ordre et
refus isolé (OFF-07), stock à vérifier (OFF-06), numéro provisoire gardé et retrouvable
(RG-T06, OFF-04), types refusés (OFF-09, Lot 2), dépense hors connexion."""

from app.domain.shared.doc_number import DocType
from tests.http.sync.conftest import Desk


def test_same_op_id_twice_is_a_duplicate_and_one_sale(desk: Desk) -> None:
    desk.enable()
    seller = desk.staff("seller")
    operation = desk.op(seller, 7, desk.sale_payload())
    [first] = desk.results(seller, operation)
    assert (first["status"], first["number"]) == ("accepted", "V-000001")
    assert first["provisional_number"] == operation["provisional_number"]
    assert first["entity_id"] == operation["op_id"]
    [again] = desk.results(seller, operation)
    assert (again["status"], again["number"], again["error"]) == ("duplicate", "V-000001", None)
    found = desk.ok("GET", f"/sales?q={operation['provisional_number']}", seller)["items"]
    assert [(s["number"], s["provisional_number"]) for s in found] == [
        ("V-000001", operation["provisional_number"])
    ]
    assert len(desk.ok("GET", "/sales?from=2026-01-01", desk.shop.owner)["items"]) == 1


def test_refused_operation_does_not_block_the_next_ones(desk: Desk) -> None:
    desk.enable()
    seller = desk.staff("seller")
    ops = [
        desk.op(seller, 1, desk.sale_payload()),
        desk.op(seller, 2, desk.sale_payload(700_000)),  # sous le minimum (UC-VEN-03)
        desk.op(seller, 3, desk.sale_payload()),
    ]
    results = desk.results(seller, *ops)
    assert [(r["status"], r["number"]) for r in results] == [
        ("accepted", "V-000001"),
        ("rejected", None),
        ("accepted", "V-000002"),
    ]
    assert results[1]["error"]["code"] == "PRICE_BELOW_MINIMUM"
    refused = desk.alerts(desk.shop.owner, "entry_refused")
    assert len(refused) == 1
    assert ops[1]["provisional_number"] in refused[0]["message"]
    [replayed] = desk.results(seller, ops[1])  # rejoué : même refus, aucune seconde alerte
    assert (replayed["status"], replayed["error"]["code"]) == ("rejected", "PRICE_BELOW_MINIMUM")
    assert len(desk.alerts(desk.shop.owner, "entry_refused")) == 1
    audit = desk.ok("GET", "/audit?module=sync", desk.shop.owner)["items"]
    assert [e["action"] for e in audit] == ["reject"]


def test_deferred_sale_below_zero_is_accepted_with_stock_to_verify(desk: Desk) -> None:
    desk.enable()
    seller = desk.staff("seller")
    [result] = desk.results(seller, desk.op(seller, 1, desk.sale_payload()))
    assert result["status"] == "accepted"
    assert [w["code"] for w in result["warnings"]] == ["STOCK_TO_VERIFY"]
    sale = desk.ok("GET", f"/sales/{result['entity_id']}", desk.shop.owner)
    assert sale["stock_to_verify"] is True
    for who in (desk.shop.owner, desk.staff("accountant")):
        assert len(desk.alerts(who, "stock_to_verify")) == 1
    online = desk.call("POST", "/sales", seller, json=desk.sale_payload())
    assert online.json()["error"]["code"] == "STOCK_INSUFFICIENT"  # en ligne : refus (TR-12)


def test_offline_expense_and_refused_operation_kinds(desk: Desk) -> None:
    desk.enable()
    accountant = desk.staff("accountant")
    expense = {"amount": 5_000, "category_id": desk.category("Carburant")}
    lot2 = desk.op(accountant, 2, {}, kind="trip_step.create")
    purchase = desk.op(accountant, 3, {}, kind="purchase.create")
    results = desk.results(
        accountant,
        desk.op(accountant, 1, expense, kind="expense.create", doc=DocType.EXPENSE),
        lot2,
        purchase,
        desk.op(accountant, 4, desk.sale_payload()),  # le comptable ne vend pas (403 → refus)
    )
    assert (results[0]["status"], results[0]["number"]) == ("accepted", "D-000001")
    codes = [r["error"]["code"] for r in results[1:]]
    assert codes == ["AVAILABLE_IN_LOT_2", "OPERATION_NOT_ALLOWED_OFFLINE", "FORBIDDEN"]
    assert results[1]["error"]["details"] == {"type": "trip_step.create", "lot": 2}
    assert len(desk.ok("GET", "/expenses", desk.shop.owner)["items"]) == 1
