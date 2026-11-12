"""Pièces jointes par HTTP (TR-17, RG-T26, ATT-01, CUS-03) : envoi multipart, lien signé
court, contenu relayé par l'API, rejeu idempotent, journal ; format, taille, stockage absent."""

from app.domain.attachments.values import MAX_SIZE_BYTES
from app.domain.catalog.ids import AttachmentId
from tests.http.attachments.conftest import GIF, JPEG, MemoryBench
from tests.http.sales.test_sales_http import sold

FORBIDDEN_WORDS = ("storage_key", "bucket", "silo", "minio", "s3")


def test_customer_id_photo_upload_link_and_relayed_content(bench: MemoryBench) -> None:
    shop, _, sale, seller = sold(bench.api)
    client_id = str(AttachmentId.new())
    fields = {"owner_type": "customer", "owner_id": sale["customer_id"], "kind": "id_document"}
    created = bench.upload(shop, seller, id=client_id, **fields)
    assert created.status_code == 201, created.text
    body = created.json()
    assert (body["id"], body["mime"], body["size_bytes"]) == (client_id, "image/jpeg", len(JPEG))
    assert (body["owner_type"], body["owner_id"], body["kind"]) == (
        "customer",
        sale["customer_id"],
        "id_document",
    )
    replay = bench.upload(shop, seller, id=client_id, **fields)
    assert (replay.status_code, replay.json()["id"]) == (200, client_id)
    assert len(bench.storage.keys()) == 1

    link = bench.link(shop, seller, client_id)
    assert link.status_code == 200, link.text
    assert link.headers["cache-control"] == "no-store"
    issued = link.json()
    prefix = f"/api/v1/shops/{shop.id}/attachments/{client_id}/content?expires="
    assert issued["url"].startswith(prefix)
    assert (issued["mime"], issued["kind"]) == ("image/jpeg", "id_document")
    assert issued["expires_at"].startswith("2026-")
    for text in (created.text, link.text):
        assert not [word for word in FORBIDDEN_WORDS if word in text.lower()]

    content = bench.open(issued["url"])
    assert content.status_code == 200, content.text
    assert content.content == JPEG
    assert content.headers["content-type"] == "image/jpeg"
    assert content.headers["x-content-type-options"] == "nosniff"
    assert content.headers["cache-control"] == "private, no-store"
    assert content.headers["content-disposition"].startswith("inline; filename=")

    journal = shop.call("GET", f"/audit/entities/attachment/{client_id}", shop.owner)
    assert journal.status_code == 200, journal.text
    [entry] = journal.json()["items"]
    assert (entry["module"], entry["action"]) == ("attachments", "create")


def test_format_size_and_rule_errors_are_400(bench: MemoryBench) -> None:
    shop, _, sale, seller = sold(bench.api)
    fields = {"owner_type": "customer", "owner_id": sale["customer_id"], "kind": "id_document"}
    for content in (GIF, b"<html>", b""):
        refused = bench.upload(shop, seller, content, **fields)
        assert refused.status_code == 400, refused.text
        assert refused.json()["error"]["code"] == "VALIDATION_ERROR"
    too_big = b"\xff\xd8\xff" + b"\x00" * (MAX_SIZE_BYTES - 2)
    heavy = bench.upload(shop, seller, too_big, **fields)
    assert heavy.status_code == 400
    assert heavy.json()["error"]["details"]["max_bytes"] == 5_242_880
    exact = bench.upload(shop, seller, too_big[:-1], **fields)
    assert exact.status_code == 201, exact.text
    owner = shop.owner
    misplaced = {"owner_type": "expense", "kind": "id_document"}
    assert bench.upload(shop, owner, **misplaced).status_code == 400
    missing_owner = {"owner_type": "customer", "kind": "id_document"}
    assert bench.upload(shop, owner, **missing_owner).status_code == 400
    garbage = {**fields, "owner_id": "pas-un-uuid"}
    assert bench.upload(shop, owner, **garbage).json()["error"]["details"]["field"] == "owner_id"
    unknown = {**fields, "kind": "selfie"}
    assert bench.upload(shop, owner, **unknown).status_code == 400
    no_file = shop.call("POST", "/attachments", owner, data=fields)
    assert no_file.status_code == 400


def test_storage_down_is_503_and_nothing_is_recorded(bench: MemoryBench) -> None:
    shop, _, sale, seller = sold(bench.api)
    bench.storage.available = False
    attachment_id = str(AttachmentId.new())
    fields = {"owner_type": "customer", "owner_id": sale["customer_id"], "kind": "id_document"}
    down = bench.upload(shop, seller, id=attachment_id, **fields)
    assert down.status_code == 503, down.text
    assert down.json()["error"]["code"] == "STORAGE_UNAVAILABLE"
    bench.storage.available = True
    assert bench.link(shop, seller, attachment_id).status_code == 404
    retried = bench.upload(shop, seller, id=attachment_id, **fields)
    assert retried.status_code == 201, retried.text
    link = bench.link(shop, seller, attachment_id).json()
    bench.storage.available = False
    assert bench.open(link["url"]).status_code == 503


def test_expense_receipt_follows_expense_rights(bench: MemoryBench) -> None:
    shop, _, _, seller = sold(bench.api)
    accountant = shop.staff["accountant"]
    fields = {"owner_type": "expense", "kind": "receipt"}
    assert bench.upload(shop, seller, **fields).status_code == 403
    created = bench.upload(shop, accountant, **fields)
    assert created.status_code == 201, created.text
    attachment_id = created.json()["id"]
    assert bench.link(shop, accountant, attachment_id).status_code == 200
    assert bench.link(shop, shop.owner, attachment_id).status_code == 200
    assert bench.link(shop, seller, attachment_id).status_code == 403
    assert bench.link(shop, shop.staff["driver"], attachment_id).status_code == 403
