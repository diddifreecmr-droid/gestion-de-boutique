"""`POST /sync` : refus de forme par opération (payload, `id`, numéro provisoire), refus du lot
(appareil, taille), `op_id` d'un autre utilisateur (droit activé)."""

from app.domain.shared.doc_number import DocType, ProvisionalDocNumber
from app.domain.shared.ids import DeviceId
from tests.http.sync.conftest import Desk


def test_each_malformed_operation_is_rejected_alone(desk: Desk) -> None:
    desk.enable()
    seller = desk.staff("seller")
    bad_payload = desk.op(seller, 1, {"kind": "cash", "lines": []})
    wrong_id = desk.op(seller, 2, {**desk.sale_payload(), "id": "x"})
    other_device = desk.op(seller, 3, desk.sale_payload())
    other_device["provisional_number"] = str(
        ProvisionalDocNumber.for_device(DocType.SALE, DeviceId.new(), 3)
    )
    wrong_type = desk.op(seller, 4, desk.sale_payload(), doc=DocType.EXPENSE)
    missing = {**desk.op(seller, 5, desk.sale_payload()), "provisional_number": None}
    garbled = {**desk.op(seller, 6, desk.sale_payload()), "provisional_number": "V-HL-xx"}
    results = desk.results(seller, bad_payload, wrong_id, other_device, wrong_type, missing,
                           garbled, desk.op(seller, 7, desk.sale_payload()))  # fmt: skip
    codes = [None if r["error"] is None else r["error"]["code"] for r in results]
    assert codes == ["VALIDATION_ERROR", "VALIDATION_ERROR", *["PROVISIONAL_NUMBER_INVALID"] * 4,
                     None]  # fmt: skip
    assert results[0]["error"]["details"]["fields"][0]["field"] == "lines"
    assert results[1]["error"]["details"] == {"field": "payload.id"}
    assert results[-1]["number"] == "V-000001"


def test_batch_level_refusals_and_foreign_op_id(desk: Desk) -> None:
    desk.enable()
    seller, owner = desk.staff("seller"), desk.shop.owner
    body = {"device_id": str(DeviceId.new()), "operations": []}
    mismatch = desk.call("POST", "/sync", seller, json=body)
    assert (mismatch.status_code, mismatch.json()["error"]["details"]) == (
        400,
        {"field": "device_id"},
    )
    too_many = [desk.op(seller, n, {}) for n in range(1, 52)]
    assert desk.sync(seller, *too_many).status_code == 400
    operation = desk.op(seller, 1, desk.sale_payload())
    assert desk.results(seller, operation)[0]["status"] == "accepted"
    foreign = desk.op(owner, 1, desk.sale_payload(), op_id=operation["op_id"])
    [conflict] = desk.results(owner, foreign)
    assert (conflict["status"], conflict["error"]["code"]) == ("rejected", "OP_ID_CONFLICT")
    naive = {**desk.op(seller, 2, {}), "captured_at": "2026-11-10T09:00:00"}
    assert desk.sync(seller, naive).status_code == 400
