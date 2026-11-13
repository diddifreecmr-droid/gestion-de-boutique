"""TEX-06 : quantité imprimée sur le reçu (« 2,5 m », « 1 pièce (5,49 m) ») ; RG-X01 et RG-X04
au dixième (QC-3) : marge d'une pièce de 5,49 m = 13 000 - 5,5 x 2 004 = 1 978."""

from decimal import Decimal

import pytest

from app.domain.catalog.ids import ArticleId
from app.domain.sales.lines import SaleLine, SaleMode
from app.domain.sales.quantity_label import length_text, quantity_label, sold_piece_length
from app.domain.shared.money import Money
from app.domain.shared.quantity import Quantity, StockUnit

PIECE = Decimal("5.49")


def _line(mode: SaleMode, quantity: str, stock: str, price: int) -> SaleLine:
    return SaleLine(
        article_id=ArticleId.new(),
        article_name="Wax Fleur de mariage",
        sale_mode=mode,
        quantity=Decimal(quantity),
        stock_quantity=Quantity.of(stock, StockUnit.METER),
        unit_price=Money(price),
        frozen_last_cost=Money(2_004),
        frozen_wac=Money(2_004),
    )


def test_labels_per_sale_mode() -> None:
    assert quantity_label(SaleMode.METER, Decimal("2.5"), None) == "2,5 m"
    assert quantity_label(SaleMode.METER, Decimal("3.0"), None) == "3 m"
    assert quantity_label(SaleMode.PIECE, Decimal(1), PIECE) == "1 pièce (5,49 m)"
    assert quantity_label(SaleMode.PIECE, Decimal(3), PIECE) == "3 pièces (5,49 m)"
    assert quantity_label(SaleMode.PIECE, Decimal(2), None) == "2 pièces"
    assert quantity_label(SaleMode.UNIT, Decimal(2), None) == "2"
    assert length_text(Decimal("10.0")) == "10 m"
    with pytest.raises(ValueError, match="non entier"):
        quantity_label(SaleMode.PIECE, Decimal("1.5"), PIECE)


def test_piece_length_shown_never_contradicts_the_stock_removed() -> None:
    one = _line(SaleMode.PIECE, "1", "5.5", 13_000)
    assert sold_piece_length(one, PIECE) == PIECE  # 1 x 5,49 → 5,5 : longueur actuelle
    assert sold_piece_length(one, Decimal("6.0")) == Decimal("5.50")  # modifiée depuis
    assert sold_piece_length(one, None) == Decimal("5.50")
    three = _line(SaleMode.PIECE, "3", "16.5", 13_000)  # 16,47 → 16,5
    assert sold_piece_length(three, PIECE) == PIECE
    assert sold_piece_length(_line(SaleMode.METER, "2.5", "2.5", 2_500), PIECE) is None


def test_scn_l3_02_margins_at_the_tenth() -> None:
    meter = _line(SaleMode.METER, "2.5", "2.5", 2_500)
    assert (meter.line_total, meter.margin) == (Money(6_250), Money(1_240))
    piece = _line(SaleMode.PIECE, "1", "5.5", 13_000)
    assert (piece.line_total, piece.margin) == (Money(13_000), Money(1_978))  # QC-3 : dixième
