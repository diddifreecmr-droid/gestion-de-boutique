"""Vente : stock insuffisant (ERR-STK-01/02), lieu du vendeur (SAL-03, Q-36), vendeur attribué,
châssis unique (RG-M01, ERR-DUP-01/03), idempotence (SAL-06), droits (RG-D03)."""

from dataclasses import replace

import pytest

from app.application.sales.inputs import SaleInput
from app.application.sales.use_cases.record_sale import RecordSaleCommand
from app.application.security.errors import PermissionDenied
from app.domain.sales.errors import ChassisAlreadySold, LocationNotAllowed
from app.domain.sales.ids import SaleId
from app.domain.sales.values import SaleKind
from app.domain.stock.errors import StockInsufficient
from tests.application.sales.test_record_sale import bought


def test_stock_insufficient_with_other_locations() -> None:
    world, owner, _, _, hj = bought()
    world.stock_in(owner, hj, "Garoua-Boulaï", 5)
    with pytest.raises(StockInsufficient) as short:  # ERR-STK-02 : 15 + 6 contrôlés ensemble
        world.record(owner, world.line(hj, 1, 15), world.line(hj, 1, 6))
    details = short.value.details
    assert (details["article_id"], details["available"], details["requested"]) == (
        str(hj.id),
        "20",
        "21",
    )
    boulai = world.loc(owner, "Garoua-Boulaï")
    assert details["other_locations"] == [
        {"location_id": str(boulai), "location_name": "Garoua-Boulaï", "available": "5"}
    ]
    assert world.matrix_total(owner, hj) == "25"  # rien n'est sorti


def test_seller_location_and_attribution() -> None:
    world, owner, _, seller, hj = bought()
    boulai = world.loc(owner, "Garoua-Boulaï")
    data = SaleInput(kind=SaleKind.CASH, lines=(world.line(hj, 0),), location_id=boulai)
    with pytest.raises(LocationNotAllowed):  # SAL-03 / Q-36
        world.sales.record.execute(seller, RecordSaleCommand(data=data))
    usual = replace(data, location_id=None)
    view, _ = world.sales.record.execute(seller, RecordSaleCommand(data=usual))
    assert view.sale.location_id == world.loc(owner, "Garoua")
    with pytest.raises(PermissionDenied):  # un vendeur n'attribue qu'à lui-même
        world.sales.record.execute(
            seller, RecordSaleCommand(data=replace(usual, seller_id=owner.user_id))
        )
    attributed, _ = world.sales.record.execute(
        owner, RecordSaleCommand(data=replace(usual, seller_id=seller.user_id))
    )
    assert attributed.sale.seller_id == seller.user_id  # le propriétaire attribue
    from app.domain.shops.errors import NotPointOfSale

    with pytest.raises(NotPointOfSale):  # entrepôt : pas un point de vente
        world.sales.record.execute(owner, RecordSaleCommand(data=data))


def test_chassis_unique_among_valid_sales() -> None:
    world, owner, _, seller, hj = bought()
    first = world.cash(seller, hj, 780_000, "LBX123")
    with pytest.raises(ChassisAlreadySold) as taken:  # ERR-DUP-01/02 : normalisé
        world.cash(seller, hj, 780_000, "lbx 123")
    assert taken.value.details["sale_number"] == "V-000001"
    assert taken.value.details["field"] == "chassis_number"
    with pytest.raises(ChassisAlreadySold) as twice:  # ERR-DUP-03 : même vente
        world.record(seller, world.line(hj, 780_000, 2, "AAA1", "aaa-1"))
    assert twice.value.details["sale_number"] is None
    from app.application.sales.use_cases.cancel_sale import CancelSaleCommand

    world.sales.cancel.execute(owner, CancelSaleCommand(sale_id=first.sale.id, reason="erreur"))
    again = world.cash(seller, hj, 780_000, "LBX123")  # SCN-06 étape 8 : châssis libéré
    assert str(again.sale.number) == "V-000002"


def test_idempotent_replay_and_rights() -> None:
    world, owner, accountant, seller, hj = bought()
    wanted = SaleId.new()
    first, created = world.record(seller, world.line(hj, 780_000), sale_id=wanted)
    again, replayed = world.record(seller, world.line(hj, 1, 3), sale_id=wanted)
    assert (created, replayed, again.sale.number) == (True, False, first.sale.number)  # SAL-06
    assert world.matrix_total(owner, hj) == "19"  # une seule sortie
    with pytest.raises(PermissionDenied):  # comptable : RG-D03
        world.cash(accountant, hj, 780_000)
