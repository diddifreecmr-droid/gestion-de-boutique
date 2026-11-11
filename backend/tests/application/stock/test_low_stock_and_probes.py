"""UC-STK-09 stock bas (LOW-01, LOW-02) ; archivage et désactivation refusés avec du stock."""

import pytest

from app.domain.alerts.alert import Alert, AlertType
from app.domain.catalog.errors import ArticleHasStock
from app.domain.shops.errors import LocationHasStock
from app.domain.stock.adjustment import AdjustmentDirection, AdjustmentReason
from app.domain.stock.values import StockCondition
from tests.application.stock.support import StockWorld


def low(alerts: list[Alert]) -> list[Alert]:
    return [alert for alert in alerts if alert.type is AlertType.LOW_STOCK]


def test_low_stock_alerts_once_and_again_after_recovery() -> None:
    world = StockWorld()
    owner, accountant, seller, _ = world.setup()
    hj = world.moto(owner, model="HJ150")  # seuil 5
    world.stock_in(owner, hj, "Garoua", 6)
    world.sell(owner, hj, "Garoua", 1)  # 5 : pas « sous » le seuil (Q-18 strict)
    assert low(world.alerts(owner, owner)) == []
    world.sell(owner, hj, "Garoua", 1)  # 4 : une alerte à O et C
    for who in (owner, accountant):
        alerts = low(world.alerts(owner, who))
        assert len(alerts) == 1
        assert alerts[0].active
    world.sell(owner, hj, "Garoua", 1)  # 3 : aucune nouvelle alerte
    assert len(low(world.alerts(owner, owner))) == 1
    assert world.alerts(owner, seller) == []
    world.stock_in(owner, hj, "Garoua", 4)  # 7 : résolue
    assert not low(world.alerts(owner, owner))[0].active
    world.sell(owner, hj, "Garoua", 3)  # 4 : nouvelle alerte
    alerts = low(world.alerts(owner, owner))
    assert [alert.active for alert in alerts] == [True, False]


def test_shop_default_threshold_applies() -> None:
    world = StockWorld()
    owner, _, _, hj = world.setup()  # sans seuil : réglage de la boutique (2), LOW-02
    world.stock_in(owner, hj, "Garoua", 3)
    world.sell(owner, hj, "Garoua", 1)
    assert low(world.alerts(owner, owner)) == []
    world.sell(owner, hj, "Garoua", 1)
    assert len(low(world.alerts(owner, owner))) == 1
    world.adjust(  # l'abîmé ne compte pas dans le stock total (Q-18)
        owner,
        hj,
        "Garoua",
        "3",
        AdjustmentDirection.IN,
        AdjustmentReason.OTHER,
        condition=StockCondition.DAMAGED,
        note="Retour abîmé",
    )
    assert low(world.alerts(owner, owner))[0].active


def test_archive_and_location_deactivation_refused_with_stock() -> None:
    world = StockWorld()
    owner, _, _, hj = world.setup()
    world.stock_in(owner, hj, "Ngaoundéré", 1)
    with pytest.raises(ArticleHasStock):  # CAT-12
        world.shops_catalog().archive.archive(owner, hj.id)
    depot = world.location(world.shop_of(owner), "Ngaoundéré")
    with pytest.raises(LocationHasStock):  # LOC-02
        world.http.locations.update(owner, depot.id, {"active": False}, depot.version)
    world.adjust(owner, hj, "Ngaoundéré", "1", reason=AdjustmentReason.LOSS)
    assert (
        world.http.locations.update(owner, depot.id, {"active": False}, depot.version).active
        is False
    )
    assert world.shops_catalog().archive.archive(owner, hj.id).is_active is False
