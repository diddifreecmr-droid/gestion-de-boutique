"""RG-X05 (TEX-04) : raccourcis pièce complète, demi-pièce, 1, 2, 3 m — au dixième (QC-3)."""

from decimal import Decimal

import pytest

from app.domain.profiles.profile import ProfileCode
from app.domain.profiles.textile import (
    ResolvedShortcut,
    SaleShortcut,
    ShortcutBasis,
    resolve_shortcut,
    shortcuts_for,
)
from app.domain.sales.lines import SaleMode

WX = {"piece_length_m": Decimal("5.49"), "sold_by_piece": True}


def _resolved(code: str, **article: object) -> ResolvedShortcut:
    shortcut = next(item for item in shortcuts_for(ProfileCode.TEXTILE) if item.code == code)
    return resolve_shortcut(shortcut, **article)  # type: ignore[arg-type]


def test_textile_serves_the_five_shortcuts_in_order_and_others_none() -> None:
    codes = [item.code for item in shortcuts_for(ProfileCode.TEXTILE)]
    assert codes == ["piece", "half_piece", "1m", "2m", "3m"]
    assert shortcuts_for(ProfileCode.MOTOS) == shortcuts_for(ProfileCode.APPAREL) == ()


def test_wax_piece_is_one_piece_and_half_piece_is_2_7_m() -> None:
    assert _resolved("piece", **WX) == ResolvedShortcut(SaleMode.PIECE, Decimal(1))
    assert _resolved("half_piece", **WX) == ResolvedShortcut(SaleMode.METER, Decimal("2.7"))
    for code, meters in (("1m", "1"), ("2m", "2"), ("3m", "3")):
        assert _resolved(code, **WX) == ResolvedShortcut(SaleMode.METER, Decimal(meters))


def test_meter_only_article_and_unknown_piece_length_use_meters() -> None:
    by_meter = {"piece_length_m": Decimal("5.49"), "sold_by_piece": False}
    assert _resolved("piece", **by_meter) == ResolvedShortcut(SaleMode.METER, Decimal("5.5"))
    unknown = {"piece_length_m": None, "sold_by_piece": False}
    assert _resolved("piece", **unknown).quantity == Decimal("5.5")  # 6 yd = 5,4864 m
    assert _resolved("half_piece", **unknown).quantity == Decimal("2.7")  # 3 yd = 2,7432 m
    assert [item.yards for item in shortcuts_for(ProfileCode.TEXTILE)[:3]] == [
        Decimal(6),
        Decimal(3),
        None,
    ]


def test_a_badly_declared_shortcut_is_refused() -> None:
    with pytest.raises(ValueError, match="longueur fixe"):
        SaleShortcut("x", "X", ShortcutBasis.PIECE, Decimal(1))
    with pytest.raises(ValueError, match="longueur fixe"):
        SaleShortcut("x", "X", ShortcutBasis.LENGTH)
    with pytest.raises(ValueError, match="dixième"):
        SaleShortcut("x", "X", ShortcutBasis.LENGTH, Decimal("1.25"))
