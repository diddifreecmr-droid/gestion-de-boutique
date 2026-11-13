"""T30 — vignettes de la recherche d'articles (UC-PAP-02 ; PHO-01, SEC-N3-01, SEC-N3-03).

`GET /articles?with_thumbnails=true` : un lien signé court par article qui a une photo
d'article, délivré après contrôle des droits, **dans la même requête** (une seule lecture des
pièces jointes) ; jamais de coût pour l'employé ; jamais le lien d'une pièce qui n'est pas une
photo d'article (pièce d'identité, justificatif, PDF) ; autre boutique → 404.
"""

from datetime import timedelta
from typing import Any

import pytest

from app.domain.catalog.ids import AttachmentId
from app.infrastructure.persistence.memory.attachments import MemoryAttachmentRepository
from tests.http.attachments.conftest import JPEG, MemoryBench
from tests.http.lot3.world import Lot3Shop, apparel_shop, keys_of, other_shop

THUMBS = "/articles?with_thumbnails=true"
COST_WORDS = ("cost", "wac", "margin", "value")
PDF = b"%PDF-1.4\n" + b"0" * 64


def _photo(bench: MemoryBench, shop: Lot3Shop, content: bytes = JPEG, **fields: str) -> str:
    sent = bench.upload(shop, shop.owner, content, **({"owner_type": "article"} | fields))
    assert sent.status_code == 201, sent.text
    return str(sent.json()["id"])


def _catalog(bench: MemoryBench) -> tuple[Lot3Shop, dict[str, Any], dict[str, Any]]:
    shop = apparel_shop(bench)
    shop.settings(min_price_enabled=True)
    photo = _photo(bench, shop, kind="photo")
    created = shop.call("POST", "/articles", shop.owner, json={
        "fields": {"name": "Chemise lin"}, "photo_id": photo,
        "base_price": 15_000, "min_price": 12_000,
    })  # fmt: skip
    assert created.status_code == 201, created.text
    ch = created.json()
    rb = shop.article({"name": "Robe pagne"}, base_price=20_000, min_price=17_000)
    shop.buy(ch, "4", 9_000)  # CMP 9 000 : sentinelle de non-fuite
    return shop, ch, rb


def _by_name(listing: dict[str, Any]) -> dict[str, Any]:
    return {item["display_name"]: item for item in listing["items"]}


def test_one_signed_link_per_photo_expiring_after_sixty_seconds(bench: MemoryBench) -> None:
    shop, _, _ = _catalog(bench)
    seller = shop.staff["seller"]
    listed = shop.call("GET", THUMBS, seller)
    assert listed.status_code == 200, listed.text
    assert listed.headers["Cache-Control"] == "no-store"
    items = _by_name(listed.json())
    assert items["Robe pagne"]["thumbnail"] is None  # pas de photo : initiales côté client
    thumbnail = items["Chemise lin"]["thumbnail"]
    opened = bench.open(thumbnail["url"])
    assert (opened.status_code, opened.content) == (200, JPEG)
    bench.clock.advance(timedelta(seconds=61))
    assert bench.open(thumbnail["url"]).status_code == 410  # PHO-01 : expiré après 60 s
    plain = shop.call("GET", "/articles", seller).json()
    assert all("thumbnail" not in item for item in plain["items"])  # pas demandé : clé absente


def test_seller_listing_has_no_cost_and_other_shop_gets_404(bench: MemoryBench) -> None:
    shop, _, _ = _catalog(bench)
    owner_view = _by_name(shop.call("GET", THUMBS, shop.owner).json())["Chemise lin"]
    assert owner_view["wac"] == 9_000  # la sentinelle existe bien
    seller_view = shop.call("GET", THUMBS, shop.staff["seller"]).json()
    assert not [k for k in keys_of(seller_view) if any(w in k for w in COST_WORDS)]
    accountant = shop.call("GET", THUMBS, shop.staff["accountant"])
    assert accountant.status_code == 200
    assert _by_name(accountant.json())["Chemise lin"]["thumbnail"] is not None
    other = other_shop(bench)
    refused = bench.api.call("GET", f"/shops/{shop.id}{THUMBS}", other.owner)
    assert refused.status_code == 404  # PHO-01 : boutique B


def test_only_article_images_get_a_link(bench: MemoryBench) -> None:
    shop = apparel_shop(bench)
    receipt = _photo(bench, shop, owner_type="expense", kind="receipt")
    pdf = _photo(bench, shop, PDF, kind="other")
    cited = {
        "Justificatif": receipt,  # rattaché à une dépense : ses droits ne sont pas ceux du stock
        "Notice": pdf,  # une vignette est une image
        "En attente": str(AttachmentId.new()),  # photo pas encore arrivée (hors connexion)
    }
    for name, photo in cited.items():
        created = shop.call("POST", "/articles", shop.owner,
                            json={"fields": {"name": name}, "photo_id": photo})  # fmt: skip
        assert created.status_code == 201, created.text
    items = _by_name(shop.call("GET", THUMBS, shop.staff["seller"]).json())
    assert {name: items[name]["thumbnail"] for name in cited} == dict.fromkeys(cited)


def test_attachments_are_read_once_for_the_whole_page(
    bench: MemoryBench, monkeypatch: pytest.MonkeyPatch
) -> None:
    shop = apparel_shop(bench)
    for index in range(3):
        photo = _photo(bench, shop, kind="photo")
        body = {"fields": {"name": f"Article {index}"}, "photo_id": photo}
        assert shop.call("POST", "/articles", shop.owner, json=body).status_code == 201
    reads: list[int] = []
    original = MemoryAttachmentRepository.find_many

    def counted(self: MemoryAttachmentRepository, ids: Any) -> Any:
        reads.append(len(ids))
        return original(self, ids)

    def one_by_one(*_: object) -> None:
        msg = "lecture d'une pièce jointe par article"
        raise AssertionError(msg)

    monkeypatch.setattr(MemoryAttachmentRepository, "find_many", counted)
    monkeypatch.setattr(MemoryAttachmentRepository, "_load", one_by_one)
    listed = shop.call("GET", THUMBS, shop.staff["seller"])
    assert listed.status_code == 200, listed.text
    assert reads == [3]
    assert all(item["thumbnail"] is not None for item in listed.json()["items"])
