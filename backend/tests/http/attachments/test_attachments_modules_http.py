"""Pièces jointes et modules (specs § 15.1) : la route est du socle, mais l'élément lié porte
son module — créance sans `receivables` → 403 `MODULE_DISABLED` à l'envoi comme au lien ;
la pièce reste en stockage et se relit à la réactivation. Les autres éléments marchent."""

from app.domain.profiles.modules import ALL_MODULES, Module
from tests.http.attachments.conftest import MemoryBench
from tests.http.catalog.test_catalog_http import Shop
from tests.http.sales.test_sales_http import sold


def _modules(bench: MemoryBench, shop: Shop, *off: Module) -> None:
    wanted = sorted(m.value for m in ALL_MODULES - set(off))
    response = bench.api.call(
        "PATCH", f"/platform/shops/{shop.id}", bench.api.admin(), json={"modules": wanted}
    )
    assert response.status_code == 200, response.text


def test_receivable_attachments_follow_the_receivables_module(bench: MemoryBench) -> None:
    shop, _, sale, seller = sold(bench.api)
    receivable = {"owner_type": "receivable", "owner_id": sale["receivable"]["id"]}
    created = bench.upload(shop, seller, kind="contract", **receivable)
    assert created.status_code == 201, created.text
    _modules(bench, shop, Module.RECEIVABLES)
    for refused in (
        bench.upload(shop, seller, kind="contract", **receivable),
        bench.link(shop, shop.owner, created.json()["id"]),
    ):
        assert refused.status_code == 403, refused.text
        assert refused.json()["error"]["details"] == {"module": "receivables"}
    customer = {"owner_type": "customer", "owner_id": sale["customer_id"]}
    assert bench.upload(shop, seller, kind="photo", **customer).status_code == 201
    _modules(bench, shop)
    assert bench.link(shop, shop.owner, created.json()["id"]).status_code == 200
