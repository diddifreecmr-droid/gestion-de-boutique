"""Recette du Lot 3, textile au dixième (QC-3) : SCN-L3-02 (RG-X01, RG-X04), SCN-L3-03
(RG-X02), TEX-01 et TEX-02 (RG-X03), prix minimum à la pièce, retour d'une ligne à la pièce."""

import pytest

from app.application.sales.returning import RefundInput, ReturnLineInput
from app.application.sales.use_cases.record_return import ReturnCommand
from app.domain.purchasing.units import EntryUnit
from app.domain.sales.errors import PriceBelowMinimum, ReturnExceedsSold
from app.domain.sales.lines import SaleMode
from app.domain.shared.errors import InvalidQuantity, ValidationFailed
from app.domain.shared.money import Money
from app.domain.stock.errors import StockInsufficient
from tests.application.sales.textile_support import STORE, TextileWorld


def _bought_wax(world: TextileWorld, **prices: int):  # type: ignore[no-untyped-def]
    wax = world.wax(**prices)
    view = world.buy(world.x_owner, wax, "10", 11_000, where=STORE, unit=EntryUnit.PIECE)
    return wax, view


def test_scn_l3_02_meter_then_pieces_at_the_tenth() -> None:
    world = TextileWorld()
    wax, purchase = _bought_wax(world)
    [line] = purchase.purchase.costed
    assert (str(line.stock_quantity), line.unit_cost) == ("54.9", Money(2_004))  # étape 1
    assert world.article(world.x_owner, wax).wac == Money(2_004)
    meter = world.sell(world.employee, wax, "2.5", 2_500).sale.content.lines[0]  # étape 2
    assert (meter.line_total, meter.margin, str(meter.stock_quantity)) == (
        Money(6_250),
        Money(1_240),
        "2.5",
    )
    assert world.matrix_total(world.x_owner, wax) == "52.4"
    piece = world.sell(world.employee, wax, "1", 13_000, SaleMode.PIECE).sale.content.lines[0]
    assert (str(piece.stock_quantity), piece.margin) == ("5.5", Money(1_978))  # étape 3
    assert world.matrix_total(world.x_owner, wax) == "46.9"
    for _ in range(8):  # étape 4 : 8 pièces passent (46,9 - 44 = 2,9)
        world.sell(world.employee, wax, "1", 13_000, SaleMode.PIECE)
    with pytest.raises(StockInsufficient) as refused:
        world.sell(world.employee, wax, "1", 13_000, SaleMode.PIECE)
    assert refused.value.details["available"] == "2.9"


def test_scn_l3_03_bought_in_yards_and_pieces() -> None:
    world = TextileWorld()
    coton = world.textile({"name": "Coton uni", "unit": "METER"})
    yards = world.buy(world.x_owner, coton, "20", 1_000, where=STORE, unit=EntryUnit.YARD)
    [line] = yards.purchase.costed
    assert (str(line.stock_quantity), line.unit_cost) == ("18.3", Money(1_093))
    half = world.buy(world.x_owner, coton, "0.5", 1_000, where=STORE, unit=EntryUnit.YARD)
    assert str(half.purchase.costed[0].stock_quantity) == "0.5"
    with pytest.raises(ValidationFailed) as refused:
        world.buy(world.x_owner, coton, "3", 11_000, where=STORE, unit=EntryUnit.PIECE)
    assert refused.value.details["field"] == "piece_length_m"


def test_tex_01_and_02_meter_precision_stock_and_piece_mode() -> None:
    world = TextileWorld()
    wax, _ = _bought_wax(world)
    view = world.sell(world.employee, wax, "2.5", 2_500)
    assert view.sale.content.lines[0].base_price == Money(2_500)  # prix de base du mètre
    with pytest.raises(InvalidQuantity):
        world.sell(world.employee, wax, "2.55", 2_500)  # au dixième seulement
    with pytest.raises(StockInsufficient) as refused:
        world.sell(world.employee, wax, "60", 2_500)
    assert refused.value.details["available"] == "52.4"  # en mètres
    coton = world.textile({"name": "Coton uni", "unit": "METER"})
    world.stock_in(world.x_owner, coton, STORE, "10")
    with pytest.raises(ValidationFailed) as no_piece:
        world.sell(world.employee, coton, "1", 5_000, SaleMode.PIECE)
    assert no_piece.value.details["field"] == "lines.sale_mode"


def test_minimum_price_of_a_piece() -> None:
    world = TextileWorld()
    world.enable_min_price(world.x_owner)
    wax, _ = _bought_wax(world, min_price=2_300, min_price_piece=12_000)
    by_meter = world.sell(world.employee, wax, "1", 2_400)  # 2 400 ≥ 2 300 : sans avertissement
    assert by_meter.warnings == ()
    low = world.sell(world.employee, wax, "1", 11_500, SaleMode.PIECE)
    [warning] = low.warnings
    assert (warning.code, warning.details["min_price"]) == ("PRICE_BELOW_MINIMUM", 12_000)
    assert world.sell(world.employee, wax, "1", 12_000, SaleMode.PIECE).warnings == ()
    world.require_price_approval(world.x_owner)
    with pytest.raises(PriceBelowMinimum):
        world.sell(world.employee, wax, "1", 11_500, SaleMode.PIECE)


def test_return_of_a_line_sold_by_the_piece() -> None:
    world = TextileWorld()
    wax, _ = _bought_wax(world)
    sold = world.sell(world.employee, wax, "2", 13_000, SaleMode.PIECE)
    assert world.matrix_total(world.x_owner, wax) == "43.9"  # 54,9 - 2 x 5,5

    def give_back(quantity: str):  # type: ignore[no-untyped-def]
        refund = RefundInput(amount=13_000, mode_id=world.mode(world.x_owner))
        command = ReturnCommand(
            sale_id=sold.sale.id,
            lines=(ReturnLineInput(line=1, quantity=quantity),),
            reason="couleur",
            refund=refund,
        )
        return world.sales.record_return.execute(world.x_owner, command)[0].sale_return

    first = give_back("1")
    [line] = first.lines
    assert (str(line.quantity), str(line.stock_quantity), line.amount) == ("1", "5.5", Money(13_000))
    assert line.margin == Money(1_978)
    assert world.matrix_total(world.x_owner, wax) == "49.4"
    with pytest.raises(InvalidQuantity):
        give_back("0.5")  # une pièce ne se rend pas à moitié
    give_back("1")
    assert world.matrix_total(world.x_owner, wax) == "54.9"  # tout le stock est revenu
    with pytest.raises(ReturnExceedsSold):
        give_back("1")
