"""« 7 rouleaux + 12 m » (décision client du 2026-11-15) et reçu « 1 rouleau (30 m) »."""

from decimal import Decimal

import pytest

from app.domain.catalog.fabric import FabricShape, clean_colors, color_article_name, color_fields
from app.domain.sales.lines import SaleMode
from app.domain.sales.quantity_label import quantity_label
from app.domain.shared.errors import ValidationFailed
from app.domain.stock.rolls import RollSplit, split_rolls


def test_split_in_whole_rolls_and_rest() -> None:
    assert split_rolls(Decimal("222.0"), Decimal(30)) == RollSplit(7, Decimal("12.0"))
    assert split_rolls(Decimal("60.0"), Decimal(30)) == RollSplit(2, Decimal("0.0"))
    assert split_rolls(Decimal("10.0"), Decimal("5.49")) == RollSplit(1, Decimal("4.5"))
    assert split_rolls(Decimal("-2.5"), Decimal(30)) is None  # stock à vérifier
    with pytest.raises(ValueError, match="strictement positive"):
        split_rolls(Decimal(1), Decimal(0))


def test_receipt_says_rouleau() -> None:
    assert quantity_label(SaleMode.PIECE, Decimal(1), Decimal(30)) == "1 rouleau (30 m)"


def test_one_article_per_color() -> None:
    assert color_article_name("Djampar", "Rouge") == "Djampar — Rouge"
    assert clean_colors([" Rouge ", "Bleu"]) == ("Rouge", "Bleu")
    for wrong in ([], ["Rouge", "rouge"], ["--"], [3]):
        with pytest.raises(ValidationFailed):
            clean_colors(wrong)
    fields = color_fields("Getzner", "Blanc", FabricShape(roll_length_m=None, meter_only=True))
    assert (fields["sold_by_piece"], fields["piece_length_m"], fields["unit"]) == (
        False,
        None,
        "METER",
    )
