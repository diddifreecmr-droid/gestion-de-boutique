"""Droits sur les pièces d'identité (SEC-N06, GUA-01, UC-CRE-07) et isolation (SEC-I14) :
propriétaire et vendeur responsable seulement ; autre vendeur → 404, comptable et chauffeur →
403 ; lien expiré après 60 s (`Clock` + 61 s) → 410 ; falsifié ou d'une autre boutique → 404."""

from datetime import timedelta
from typing import Any

from tests.http.attachments.conftest import MemoryBench, add_seller
from tests.http.catalog.test_catalog_http import Shop
from tests.http.sales.test_sales_http import sold
from tests.http.shops.conftest import Session


class OtherShop:
    """Boutique B (propriétaire seul) : ses identifiants ne doivent jamais servir chez A."""

    def __init__(self, bench: MemoryBench) -> None:
        self.api = bench.api
        opened = bench.api.open_motos(bench.api.admin(), owner_phone="690000077")
        self.id = opened["shop"]["shop_id"]
        self.owner = bench.api.login("690000077", opened["temporary_pin"])

    def call(self, method: str, suffix: str, who: Session, **kwargs: Any) -> Any:
        return self.api.call(method, f"/shops/{self.id}{suffix}", who, **kwargs)


def _guarantor_id_photo(bench: MemoryBench) -> tuple[Shop, Session, str]:
    shop, _, sale, seller = sold(bench.api)
    fields = {"owner_type": "receivable", "owner_id": sale["receivable"]["id"]}
    created = bench.upload(shop, seller, kind="id_document", **fields)
    assert created.status_code == 201, created.text
    attachment_id = created.json()["id"]
    guarantor = {"name": "Ali", "phone": "699000003", "id_doc_photo_id": attachment_id}
    rid = sale["receivable"]["id"]
    added = shop.call("POST", f"/receivables/{rid}/guarantors", seller, json=guarantor)
    assert added.status_code == 201, added.text
    return shop, seller, attachment_id


def test_id_photo_is_for_the_owner_and_the_responsible_seller_only(bench: MemoryBench) -> None:
    shop, seller, attachment_id = _guarantor_id_photo(bench)
    seller2 = add_seller(shop, "677000009")
    assert bench.link(shop, shop.owner, attachment_id).status_code == 200
    assert bench.link(shop, seller, attachment_id).status_code == 200
    other = bench.link(shop, seller2, attachment_id)
    assert other.status_code == 404
    assert other.json()["error"]["code"] == "NOT_FOUND"
    for role in ("accountant", "driver"):
        refused = bench.link(shop, shop.staff[role], attachment_id)
        assert refused.status_code == 403, role
    admin = bench.api.admin()
    assert bench.link(shop, admin, attachment_id).status_code == 404  # sans délégation
    assert shop.call("POST", "/admin-access", shop.owner).status_code == 201
    assert bench.link(shop, admin, attachment_id).status_code == 403  # délégué : pas les CNI
    audit = shop.call("GET", "/audit?action=access_denied", shop.owner).json()["items"]
    assert len(audit) >= 3  # refus journalisés (RG-D01)


def test_upload_rights_follow_the_linked_element(bench: MemoryBench) -> None:
    shop, _, sale, _ = sold(bench.api)
    seller2 = add_seller(shop, "677000010")
    customer = {"owner_type": "customer", "owner_id": sale["customer_id"], "kind": "id_document"}
    assert bench.upload(shop, seller2, **customer).status_code == 404  # client d'un autre
    assert bench.upload(shop, shop.staff["accountant"], **customer).status_code == 403
    receivable = {**customer, "owner_type": "receivable", "owner_id": sale["receivable"]["id"]}
    assert bench.upload(shop, seller2, **receivable).status_code == 404
    unknown = {**customer, "owner_id": sale["receivable"]["id"]}  # pas un client
    assert bench.upload(shop, shop.owner, **unknown).status_code == 404
    assert bench.storage.keys() == []


def test_a_link_expires_after_sixty_seconds_and_cannot_be_forged(bench: MemoryBench) -> None:
    shop, seller, attachment_id = _guarantor_id_photo(bench)
    url = bench.link(shop, seller, attachment_id).json()["url"]
    path, _, query = url.partition("?")
    expires, signature = (part.split("=", 1)[1] for part in query.split("&"))
    forged = f"{path}?expires={int(expires) + 3600}&signature={signature}"
    assert bench.open(forged).status_code == 404
    assert bench.open(f"{path}?expires={expires}&signature={'A' * 43}").status_code == 404
    assert bench.open(path).status_code == 400  # sans signature
    bench.clock.advance(timedelta(seconds=60))
    assert bench.open(url).status_code == 200
    bench.clock.advance(timedelta(seconds=1))
    expired = bench.open(url)
    assert expired.status_code == 410
    assert expired.json()["error"]["code"] == "LINK_EXPIRED"
    fresh = bench.link(shop, seller, attachment_id).json()["url"]
    assert bench.open(fresh).status_code == 200


def test_another_shop_never_reaches_an_attachment(bench: MemoryBench) -> None:
    shop, seller, attachment_id = _guarantor_id_photo(bench)
    other = OtherShop(bench)
    assert other.call("GET", f"/attachments/{attachment_id}/url", other.owner).status_code == 404
    reached = bench.api.call(
        "GET", f"/shops/{shop.id}/attachments/{attachment_id}/url", other.owner
    )
    assert reached.status_code == 404  # non-membre de A
    url = bench.link(shop, seller, attachment_id).json()["url"]
    moved = url.replace(f"/shops/{shop.id}/", f"/shops/{other.id}/")
    assert bench.open(moved).status_code == 404  # signature liée à la boutique A
    receipt = bench.upload(other, other.owner, owner_type="expense", kind="receipt")
    assert receipt.status_code == 201, receipt.text
    foreign = receipt.json()["id"]
    assert bench.link(shop, shop.owner, foreign).status_code == 404
