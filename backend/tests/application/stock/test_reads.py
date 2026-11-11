"""Lectures : matrice (UC-STK-05), valeur (UC-STK-10), abîmé, historique (UC-STK-06)."""

import pytest

from app.application.ports.pagination import PageRequest
from app.application.security.errors import PermissionDenied
from app.application.stock.use_cases.stock_matrix import MatrixOrder, StockBadge
from app.domain.shared.errors import NotFound
from app.domain.shared.roles import Role
from app.domain.shops.ids import LocationId
from app.domain.stock.adjustment import AdjustmentDirection, AdjustmentReason
from app.domain.stock.values import StockCondition
from tests.application.stock.support import StockWorld


def test_matrix_columns_filter_sort_and_badges() -> None:
    world = StockWorld()
    owner, _, seller, hj = world.setup()
    dk = world.moto(owner, model="DK150")
    boxer = world.moto(owner, brand="Bajaj", model="Boxer")
    world.stock_in(owner, hj, "Garoua", 1)
    world.stock_in(owner, hj, "Garoua-Boulaï", 9)
    world.stock_in(owner, dk, "Garoua", 3)
    matrix = world.stock_http.matrix.execute(seller)
    assert [loc.name for loc in matrix.locations] == [
        "Garoua-Boulaï",
        "Ngaoundéré",
        "Garoua",
    ]  # ordre d'affichage
    rows = {row.article.display_name: row for row in matrix.rows}
    assert [row.article.id for row in matrix.rows] == [boxer.id, dk.id, hj.id]
    assert (str(rows["Haojue HJ125-8"].total), rows["Haojue HJ125-8"].badge) == (
        "10",
        StockBadge.OK,
    )
    assert (rows["Haojue DK150"].badge, rows["Bajaj Boxer"].badge) == (
        StockBadge.LOW,
        StockBadge.OUT,
    )
    assert matrix.visibility.costs is False
    garoua = world.loc(owner, "Garoua")
    only = world.stock_http.matrix.execute(
        owner, text="haojue", location_id=garoua, order=MatrixOrder.QUANTITY_DESC
    )
    assert [loc.name for loc in only.locations] == ["Garoua"]
    assert [(r.article.id, str(r.total)) for r in only.rows] == [(dk.id, "3"), (hj.id, "1")]
    ascending = world.stock_http.matrix.execute(owner, order=MatrixOrder.QUANTITY_ASC)
    assert [r.article.id for r in ascending.rows] == [boxer.id, dk.id, hj.id]
    with pytest.raises(NotFound):
        world.stock_http.matrix.execute(owner, location_id=LocationId.new())
    driver = world.staff(owner, Role.DRIVER)
    with pytest.raises(PermissionDenied):
        world.stock_http.matrix.execute(driver)


def test_value_report_partial_and_separate_damaged() -> None:
    world = StockWorld()
    owner, accountant, seller, hj = world.setup()
    dk = world.moto(owner, model="DK150")
    world.stock_in(owner, hj, "Garoua", 2)
    world.stock_in(owner, dk, "Garoua", 1)
    world.set_costs(owner, hj, 550_000, 530_000)
    world.adjust(
        owner,
        hj,
        "Garoua",
        "1",
        AdjustmentDirection.IN,
        AdjustmentReason.OTHER,
        condition=StockCondition.DAMAGED,
        note="Rayure",
    )
    report = world.stock_http.value.execute(accountant)
    total = report.sellable
    assert (total.at_wac, total.at_wac_known.amount, total.without_wac) == (None, 1_060_000, 1)
    assert total.at_last_cost_known.amount == 1_100_000
    assert report.damaged.at_wac is not None
    assert report.damaged.at_wac.amount == 530_000
    assert report.incoming.at_wac is not None
    assert report.incoming.at_wac.amount == 0
    garoua = next(line for line in report.locations if line.location.name == "Garoua")
    assert garoua.sellable.without_wac == 1
    world.set_costs(owner, dk, 900_000, 900_000)
    assert world.stock_http.value.execute(owner).sellable.at_wac is not None
    with pytest.raises(PermissionDenied):
        world.stock_http.value.execute(seller)
    damaged = world.stock_http.damaged.execute(accountant)
    assert [(line.article.id, str(line.level.damaged)) for line in damaged.lines] == [(hj.id, "1")]
    with pytest.raises(PermissionDenied):
        world.stock_http.damaged.execute(seller)


def test_history_hides_sale_documents_from_accountant() -> None:
    world = StockWorld()
    owner, accountant, seller, hj = world.setup()
    world.stock_in(owner, hj, "Garoua", 3)
    world.sell(owner, hj, "Garoua", 1)
    history = world.stock_http.movements.execute(accountant, hj.id, PageRequest(limit=1))
    assert history.visibility.sales_documents is False
    assert history.visibility.costs is True
    assert history.page.next_cursor is not None
    rest = world.stock_http.movements.execute(
        accountant, hj.id, PageRequest(1, history.page.next_cursor)
    )
    assert [m.id for m in rest.page.items] != [m.id for m in history.page.items]
    assert world.stock_http.movements.execute(
        owner, hj.id, PageRequest()
    ).visibility.sales_documents
    with pytest.raises(PermissionDenied):  # STK-05
        world.stock_http.movements.execute(seller, hj.id, PageRequest())
