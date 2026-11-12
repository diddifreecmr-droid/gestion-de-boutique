"""RG-T09 sur la vente par HTTP (ERR-DAT-01 à 04, 07 à 09) : journée de Douala, 7 jours en
arrière pour le vendeur, aucune date future, propriétaire sans borne passée, heure de saisie
de l'appareil refusée au-delà de 10 min dans le futur (décision Q8, specs § 15.1).
Horloge : mardi 10/11/2026 09:00Z (10:00 à Douala)."""

from datetime import UTC, datetime
from typing import Any

from app.infrastructure.persistence.memory.clock import FixedClock
from tests.http.recette.routes_trade import cash_sale
from tests.http.recette.world import Side, World

SELLER_PHONE = "677000000"  # vendeur V de la boutique A (world.py)


def dated(side: Side, who: Any, day: str, **headers: str) -> Any:
    body = {**cash_sale(side), "sold_on": day}
    return side.call("POST", "/sales", who, json=body, headers=headers or None)


def _error(response: Any) -> tuple[int, str | None]:
    code = response.json().get("error", {}).get("code")
    return response.status_code, code


def test_seller_window_and_owner_without_past_limit(world: World) -> None:
    side = world.a
    seller = side.sessions["seller"]
    assert dated(side, seller, "2026-11-03").status_code == 201  # J-7 inclus (ERR-DAT-01)
    before = dated(side, seller, "2026-11-02")  # J-8 (ERR-DAT-02)
    assert _error(before) == (422, "DATE_OUT_OF_RANGE")
    assert before.json()["error"]["details"]["min_date"] == "2026-11-03"
    for who in (seller, side.owner):  # ERR-DAT-03 : futur refusé à tous
        assert _error(dated(side, who, "2026-11-11")) == (422, "DATE_OUT_OF_RANGE")
    assert dated(side, side.owner, "2025-01-01").status_code == 201  # ERR-DAT-04


def test_the_business_day_is_the_one_of_douala(world: World) -> None:
    side = world.a
    clock = world.api.identity.clock
    assert isinstance(clock, FixedClock)
    clock.move_to(datetime(2026, 11, 10, 23, 30, tzinfo=UTC))  # 11/11 00:30 à Douala
    seller = world.relogin(SELLER_PHONE)
    assert dated(side, seller, "2026-11-11").status_code == 201  # ERR-DAT-07
    clock.move_to(datetime(2026, 11, 10, 22, 30, tzinfo=UTC))  # 10/11 23:30 à Douala
    seller = world.relogin(SELLER_PHONE)
    assert _error(dated(side, seller, "2026-11-11")) == (422, "DATE_OUT_OF_RANGE")  # ERR-DAT-08


def test_device_capture_time_at_most_ten_minutes_ahead(world: World) -> None:
    side = world.a  # ERR-DAT-09 : horloge de l'appareil fausse
    seller = side.sessions["seller"]
    late = {"X-Captured-At": "2026-11-10T10:11:00+01:00"}  # 11 min d'avance
    assert _error(dated(side, seller, "2026-11-10", **late)) == (422, "DATE_OUT_OF_RANGE")
    near = {"X-Captured-At": "2026-11-10T10:09:00+01:00"}  # 9 min : accepté
    assert dated(side, seller, "2026-11-10", **near).status_code == 201
