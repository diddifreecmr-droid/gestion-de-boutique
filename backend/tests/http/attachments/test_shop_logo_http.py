"""Logo de la boutique (specs § 15.1, 2026-11-24) : envoi par le gérant seul (pièce `shop`),
désigné puis retiré dans les réglages ; lien signé court dans le profil (tout membre) et dans
le reçu si « afficher le logo » ; PDF refusé ; pièce d'une autre boutique → 404."""

from typing import Any

from tests.http.attachments.conftest import MemoryBench
from tests.http.attachments.test_attachments_rights_http import OtherShop
from tests.http.catalog.test_catalog_http import Shop
from tests.http.sales.test_sales_http import sold
from tests.http.shops.conftest import Session

PNG = b"\x89PNG\r\n\x1a\n" + bytes(range(256)) * 4
PDF = b"%PDF-1.4\n" + b"0" * 64
SHOP_LOGO = {"owner_type": "shop", "kind": "photo"}


def _upload(bench: MemoryBench, shop: Any, who: Session, content: bytes = PNG) -> Any:
    return bench.upload(shop, who, content, **SHOP_LOGO)


def _set_logo(shop: Any, logo_id: str | None, **extra: object) -> Any:
    version = shop.call("GET", "/settings", shop.owner).json()["version"]
    body = {"version": version, "logo_attachment_id": logo_id, **extra}
    return shop.call("PATCH", "/settings", shop.owner, json=body)


def _logo_of(shop: Shop, who: Session) -> Any:
    found = shop.call("GET", "/profile", who)
    assert found.status_code == 200, found.text
    return found.json()["logo"]


def test_owner_sets_logo_every_member_reads_it_and_owner_removes_it(bench: MemoryBench) -> None:
    shop = Shop(bench.api)
    assert _logo_of(shop, shop.owner) is None  # logo générique côté écran
    sent = _upload(bench, shop, shop.owner)
    assert sent.status_code == 201, sent.text
    logo_id = sent.json()["id"]
    changed = _set_logo(shop, logo_id)
    assert changed.status_code == 200, changed.text
    assert changed.json()["logo_attachment_id"] == logo_id
    for who in (shop.owner, shop.staff["seller"], shop.staff["accountant"]):
        logo = _logo_of(shop, who)
        assert logo is not None
        opened = bench.open(logo["url"])
        assert opened.status_code == 200
        assert opened.content == PNG
    removed = _set_logo(shop, None)
    assert removed.status_code == 200, removed.text
    assert removed.json()["logo_attachment_id"] is None
    assert _logo_of(shop, shop.staff["seller"]) is None


def test_only_the_owner_uploads_the_logo(bench: MemoryBench) -> None:
    shop = Shop(bench.api)
    for role in ("seller", "accountant", "driver"):
        refused = _upload(bench, shop, shop.staff[role])
        assert refused.status_code == 403, role
    assert bench.storage.keys() == []
    logo_id = _upload(bench, shop, shop.owner).json()["id"]
    version = shop.call("GET", "/settings", shop.owner).json()["version"]
    body = {"version": version, "logo_attachment_id": logo_id}
    patched = shop.call("PATCH", "/settings", shop.staff["accountant"], json=body)
    assert patched.status_code == 403


def test_logo_must_be_a_shop_image_of_this_shop(bench: MemoryBench) -> None:
    shop = Shop(bench.api)
    pdf = _upload(bench, shop, shop.owner, PDF)
    assert pdf.status_code == 201, pdf.text
    refused = _set_logo(shop, pdf.json()["id"])
    assert refused.status_code == 400
    assert refused.json()["error"]["details"]["field"] == "logo_attachment_id"
    article_photo = bench.upload(shop, shop.owner, PNG, owner_type="article", kind="photo")
    assert _set_logo(shop, article_photo.json()["id"]).status_code == 400
    other = OtherShop(bench)
    foreign = _upload(bench, other, other.owner)
    assert foreign.status_code == 201, foreign.text
    assert _set_logo(shop, foreign.json()["id"]).status_code == 404  # aucune fuite
    assert _logo_of(shop, shop.owner) is None


def test_receipt_carries_the_logo_only_when_shown(bench: MemoryBench) -> None:
    shop, _, sale, seller = sold(bench.api)
    logo_id = _upload(bench, shop, shop.owner).json()["id"]
    assert _set_logo(shop, logo_id, show_logo=True).status_code == 200
    path = f"/sales/{sale['id']}/receipt"
    header = shop.call("GET", path, seller).json()["header"]
    assert header["show_logo"] is True
    assert bench.open(header["logo_url"]).content == PNG
    assert _set_logo(shop, logo_id, show_logo=False).status_code == 200
    hidden = shop.call("GET", path, seller).json()["header"]
    assert hidden["logo_url"] is None
