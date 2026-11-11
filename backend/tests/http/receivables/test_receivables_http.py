"""Routes des créances : contrat (SCN-01 7, SCN-07, SCN-08 par HTTP), droits M18 à M22
(comptable et chauffeur : 403 ; créance ancienne et perte : propriétaire), idempotence,
`OVERPAYMENT`, reçu de versement, rappels, garants (pièce visible du responsable), relevé."""

from typing import Any

from app.domain.receivables.ids import InstallmentId, ReceivableId
from tests.http.sales.test_sales_http import cash_mode, sold
from tests.http.shops.conftest import Api


def test_receivable_installments_receipt_and_rights(api: Api) -> None:
    shop, _, sale, seller = sold(api)
    owner, accountant = shop.owner, shop.staff["accountant"]
    rid, mode = sale["receivable"]["id"], cash_mode(shop)
    listing = shop.call("GET", "/receivables", seller)
    assert listing.status_code == 200, listing.text
    body = listing.json()
    assert body["summary"] == {"total_due": 480_000, "debtor_count": 1, "received_today": 0}
    [item] = body["items"]
    assert (item["id"], item["initial_amount"], item["status"]) == (rid, 480_000, "open")
    assert (item["sale_number"], item["seniority_band"]) == ("V-000001", "under_30")
    assert item["reminders"][0]["remind_on"] == "2026-12-01"
    for who in (accountant, shop.staff["driver"]):
        assert shop.call("GET", "/receivables", who).status_code == 403
        assert shop.call("GET", f"/receivables/{rid}", who).status_code == 403
    payment: dict[str, Any] = {"id": str(InstallmentId.new()), "amount": 200_000, "mode_id": mode}
    paid = shop.call("POST", f"/receivables/{rid}/installments", seller, json=payment)
    assert paid.status_code == 201, paid.text
    installment = paid.json()["installment"]
    assert (installment["number"], paid.json()["receivable"]["remaining"]) == ("R-000001", 280_000)
    replay = shop.call("POST", f"/receivables/{rid}/installments", seller, json=payment)
    assert (replay.status_code, replay.json()["installment"]["number"]) == (200, "R-000001")
    too_much = {"amount": 300_000, "mode_id": mode}
    refused = shop.call("POST", f"/receivables/{rid}/installments", seller, json=too_much)
    assert refused.status_code == 422
    assert refused.json()["error"]["code"] == "OVERPAYMENT"
    assert refused.json()["error"]["details"]["remaining"] == 280_000
    receipt = shop.call("GET", f"/installments/{installment['id']}/receipt", seller).json()
    assert (receipt["total_paid"], receipt["remaining"], receipt["settled"]) == (
        500_000,
        280_000,
        False,
    )
    customer = sale["customer_id"]
    rest = shop.call(
        "POST",
        f"/customers/{customer}/installments",
        seller,
        json={"amount": 280_000, "mode_id": mode},
    )
    assert rest.status_code == 201, rest.text
    assert rest.json()["receivable"]["status"] == "settled"
    last = rest.json()["installment"]["id"]
    assert shop.call("GET", f"/installments/{last}/receipt", seller).json()["settled"]
    reason = {"reason": "chèque sans provision"}
    assert shop.call("POST", f"/installments/{last}/cancel", seller, json=reason).status_code == 403
    assert shop.call("POST", f"/installments/{last}/cancel", owner, json={}).status_code == 400
    cancelled = shop.call("POST", f"/installments/{last}/cancel", owner, json=reason)
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["receivable"]["status"] == "open"
    statement = shop.call("GET", f"/customers/{customer}/statement", seller)
    assert statement.status_code == 200, statement.text
    kinds = [(line["kind"], line["balance_after"]) for line in statement.json()["lines"]]
    assert kinds[:3] == [("sale", 780_000), ("deposit", 480_000), ("installment", 280_000)]
    assert statement.json()["total_due"] == 280_000
    assert shop.call("GET", f"/customers/{customer}/statement", accountant).status_code == 403


def test_legacy_write_off_follow_up_and_guarantor(api: Api) -> None:
    shop, _, sale, seller = sold(api)
    owner, rid = shop.owner, sale["receivable"]["id"]
    legacy: dict[str, Any] = {
        "id": str(ReceivableId.new()),
        "customer": {"id": None, "name": "Ali B.", "phone": "+237699000001"},
        "amount": 300_000,
        "opened_on": "2026-03-01",
        "description": "1 moto Haojue, cahier 2026",
    }
    assert shop.call("POST", "/receivables", seller, json=legacy).status_code == 403
    created = shop.call("POST", "/receivables", owner, json=legacy)
    assert created.status_code == 201, created.text
    assert shop.call("POST", "/receivables", owner, json=legacy).status_code == 200
    old = created.json()
    assert (old["origin"], old["seniority_band"], old["sale_id"]) == ("legacy", "over_90", None)
    path = f"/receivables/{old['id']}/write-off"
    assert shop.call("POST", path, seller, json={"reason": "parti"}).status_code == 403
    lost = shop.call("POST", path, owner, json={"reason": "client parti"})
    assert lost.status_code == 200, lost.text
    assert lost.json()["status"] == "written_off"
    again = shop.call("POST", path, owner, json={"reason": "client parti"})
    assert again.json()["error"]["code"] == "INVALID_STATE_TRANSITION"
    patch = {"version": 1, "responsible_seller_id": None}
    assert shop.call("PATCH", f"/receivables/{rid}", seller, json=patch).status_code == 403
    terms = shop.call("PATCH", f"/receivables/{rid}", seller, json={"version": 1, "terms": "ok"})
    assert (terms.status_code, terms.json()["terms"]) == (200, "ok")
    planned = shop.call(
        "POST", f"/receivables/{rid}/reminders", seller, json={"remind_on": "2027-01-15"}
    )
    assert planned.status_code == 201, planned.text
    reminder = planned.json()["reminders"][-1]["id"]
    done = shop.call("PATCH", f"/reminders/{reminder}", seller, json={"status": "done"})
    assert done.json()["reminders"][-1]["status"] == "done"
    guarantor = {
        "name": "Issa A.",
        "phone": "699112233",
        "relation": "frère",
        "id_doc_type": "national_id",
        "id_doc_number": "CNI-9",
    }
    added = shop.call("POST", f"/receivables/{rid}/guarantors", seller, json=guarantor)
    assert added.status_code == 201, added.text
    assert added.json()["guarantors"][0]["id_doc_number"] == "CNI-9"  # vendeur responsable
    accountant = shop.staff["accountant"]
    assert (
        shop.call("POST", f"/receivables/{rid}/guarantors", accountant, json=guarantor).status_code
        == 403
    )
    moved = shop.call("PATCH", f"/receivables/{rid}", owner, json={**patch, "version": 5})
    assert moved.status_code == 200, moved.text
    assert shop.call("GET", f"/receivables/{rid}", seller).status_code == 404  # plus la sienne
    hidden = shop.call("GET", f"/receivables/{rid}", owner).json()["guarantors"][0]
    assert hidden["id_doc_number"] == "CNI-9"  # propriétaire : visible
