"""Champs d'article validés par le schéma du profil, clés pliées (CAT-01, CAT-02, Q-33)."""

from decimal import Decimal

import pytest

from app.domain.catalog.keys import fold, identity_key, search_key, sort_key
from app.domain.catalog.schema import read_profile_fields
from app.domain.profiles.apparel import APPAREL, TEXTILE
from app.domain.profiles.motos import MOTOS
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.quantity import StockUnit


def test_fold_ignores_case_accents_spaces_and_punctuation() -> None:
    assert fold("  Haojue   HJ125-8 ") == "haojue hj125 8"
    assert fold("Ngaoundéré ÉTÉ") == "ngaoundere ete"
    assert identity_key("haojue", "hj125 8") == identity_key("HAOJUE", "HJ125-8")
    assert search_key(["Wax « Fleur »", None, "WX-0087"]) == "wax fleur wx 0087"
    assert sort_key("Haojue HJ125-8") == "haojuehj1258"


def test_motos_display_name_is_brand_and_model() -> None:
    fields = read_profile_fields(
        MOTOS, {"brand": " Haojue ", "model": "HJ125-8", "engine_cc": 125, "category": None}
    )
    assert fields.display_name == "Haojue HJ125-8"
    assert (fields.brand, fields.model, fields.reference) == ("Haojue", "HJ125-8", None)
    assert fields.stock_unit is StockUnit.UNIT
    assert fields.attributes == {"engine_cc": 125}


@pytest.mark.parametrize(
    ("values", "detail"),
    [
        ({"brand": "Haojue"}, "field"),  # modèle obligatoire (texte : champ nommé)
        ({"brand": "Haojue", "model": "X", "color": "rouge"}, "fields"),  # champ inconnu
        ({"brand": "Haojue", "model": "X", "engine_cc": "125"}, "field"),
        ({"brand": "Haojue", "model": "X", "engine_cc": True}, "field"),
        ({"brand": "Haojue", "model": "X", "engine_cc": 0}, "field"),
        ({"brand": "---", "model": "X"}, "field"),  # aucune lettre ni chiffre
        ({"brand": "H" * 121, "model": "X"}, "field"),
    ],
)
def test_motos_rejects_invalid_fields(values: dict[str, object], detail: str) -> None:
    with pytest.raises(ValidationFailed) as caught:
        read_profile_fields(MOTOS, values)
    assert detail in caught.value.details


def test_apparel_name_reference_and_attributes() -> None:
    fields = read_profile_fields(
        APPAREL, {"name": "Chemise lin", "reference": "CH-0142", "type": "Chemise"}
    )
    assert (fields.display_name, fields.reference, fields.stock_unit) == (
        "Chemise lin",
        "CH-0142",
        StockUnit.PIECE,
    )
    assert fields.attributes == {"type": "Chemise"}
    assert read_profile_fields(APPAREL, {"name": "Robe", "brand": "Zara"}).brand == "Zara"


def test_textile_unit_and_piece_rules() -> None:
    wax = read_profile_fields(
        TEXTILE,
        {"name": "Wax", "unit": "METER", "sold_by_piece": True, "piece_length_m": "5.49"},
    )
    assert (wax.stock_unit, wax.sold_by_piece, wax.piece_length_m) == (
        StockUnit.METER,
        True,
        Decimal("5.49"),
    )
    bad: list[dict[str, object]] = [
        {"name": "Wax", "unit": "YARD"},
        {"name": "Wax"},  # unité obligatoire
        {"name": "Wax", "unit": "PIECE", "sold_by_piece": True, "piece_length_m": "5"},
        {"name": "Wax", "unit": "METER", "sold_by_piece": True},
        {"name": "Wax", "unit": "METER", "piece_length_m": "5"},
        {"name": "Wax", "unit": "METER", "sold_by_piece": True, "piece_length_m": "5.491"},
        {"name": "Wax", "unit": "METER", "sold_by_piece": True, "piece_length_m": "0"},
        {"name": "Wax", "unit": "METER", "sold_by_piece": True, "piece_length_m": 5.4},
        {"name": "Wax", "unit": "METER", "sold_by_piece": True, "piece_length_m": "abc"},
        {"name": "Wax", "unit": "METER", "sold_by_piece": "oui"},
    ]
    for values in bad:
        with pytest.raises(ValidationFailed):
            read_profile_fields(TEXTILE, values)
