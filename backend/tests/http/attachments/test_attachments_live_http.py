"""De bout en bout sur le stockage du banc (`--storage=s3` : Silo de dev, infra/README.md) :
envoi d'une photo de pièce d'identité, lien signé, contenu relu octet pour octet par l'API."""

from app.application.attachments.ports import FileStorage
from tests.http.attachments.conftest import JPEG, Bench
from tests.http.sales.test_sales_http import sold


def test_round_trip_through_the_configured_storage(live_bench: Bench[FileStorage]) -> None:
    shop, _, sale, seller = sold(live_bench.api)
    fields = {"owner_type": "receivable", "owner_id": sale["receivable"]["id"]}
    created = live_bench.upload(shop, seller, kind="id_document", **fields)
    assert created.status_code == 201, created.text
    link = live_bench.link(shop, seller, created.json()["id"])
    assert link.status_code == 200, link.text
    content = live_bench.open(link.json()["url"])
    assert (content.status_code, content.content) == (200, JPEG)
