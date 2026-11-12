"""SEC-M (critère A10) : la matrice § 4.2 cellule par cellule, par **appel direct à l'API**.

Pour chaque ligne : une boutique neuve ; les rôles refusés d'abord (aucun effet possible),
puis les rôles autorisés, le propriétaire en dernier. Chaque 403 `FORBIDDEN` doit créer
**exactement une** entrée « Accès refusé » au journal de la boutique (RG-D01).
"""

from typing import Any

import pytest

from tests.http.recette.matrix import LOT2_PATHS, ROLES, ROWS, SETUP, Cell
from tests.http.recette.paths import url
from tests.http.recette.routes import ROUTES
from tests.http.recette.world import Side, World

GRANTED = {200, 201, 204, 409, 422}  # 409/422 : refus métier, donc droit déjà accordé
ORDER = {"-": 0, "f": 0, "n": 1, "Y": 2}


def denied_count(side: Side) -> int:
    total, cursor = 0, None
    while True:
        params: dict[str, Any] = {"action": "access_denied", "limit": 200}
        if cursor:
            params["cursor"] = cursor
        page = side.ok("GET", "/audit", side.owner, params=params)
        total += len(page["items"])
        cursor = page["next_cursor"]
        if cursor is None:
            return total


def _check(side: Side, cell: Cell, role: str, letter: str) -> tuple[str | None, bool]:
    """(écart éventuel, vrai si la réponse est un 403 `FORBIDDEN`)."""
    method, template = cell.route.split(" ", 1)
    factory = cell.body or ROUTES[cell.route]
    body = factory(side) if factory else None
    response = side.call(method, url(side, template, cell.overrides), side.sessions[role],
                         json=body)  # fmt: skip
    status = response.status_code
    code = response.json()["error"]["code"] if status >= 400 and response.content else None
    expected = {"Y": "accordé", "-": "403 FORBIDDEN", "n": "404", "f": "403 FEATURE_DISABLED"}
    ok = {
        "Y": status in GRANTED,
        "-": (status, code) == (403, "FORBIDDEN"),
        "n": status == 404,
        "f": (status, code) == (403, "FEATURE_DISABLED"),
    }[letter]
    gap = None if ok else f"{cell.route} [{role}] : {status} {code} (attendu {expected[letter]})"
    return gap, (status, code) == (403, "FORBIDDEN")


@pytest.mark.parametrize("row", list(ROWS))
def test_row_of_the_rights_matrix(world: World, row: str) -> None:
    side = world.a
    if row in SETUP:
        SETUP[row](side)
    before = denied_count(side)
    gaps, refusals = [], 0
    for cell in ROWS[row]:
        plan = sorted(zip(ROLES, cell.letters, strict=True), key=lambda rl: ORDER[rl[1]])
        plan.sort(key=lambda rl: rl[0] == "owner")  # propriétaire en dernier
        for role, letter in plan:
            gap, refused = _check(side, cell, role, letter)
            gaps += [gap] if gap else []
            refusals += refused
    assert gaps == []
    assert denied_count(side) - before == refusals  # un 403 = une entrée « Accès refusé »


def test_m16_seller_below_minimum_gets_a_warning_not_a_refusal(world: World) -> None:
    side = world.a
    sale = side.ok("POST", "/sales", side.sessions["seller"], json=ROWS["M16"][0].body(side))  # type: ignore[misc]
    assert [w["code"] for w in sale["warnings"]] == ["PRICE_BELOW_MINIMUM"]


def test_m28_me_and_m29_platform_console(world: World) -> None:
    side = world.a
    for role in ROLES:
        who = side.sessions[role]
        assert world.api.call("GET", "/me", who).status_code == 200
        for method in ("GET", "POST"):
            refused = world.api.call(
                method, "/platform/shops", who, json={} if method == "POST" else None
            )
            assert (refused.status_code, refused.json()["error"]["code"]) == (403, "FORBIDDEN")
        patch = world.api.call("PATCH", f"/platform/shops/{side.id}", who, json={})
        assert patch.status_code == 403
    assert world.api.call("GET", "/platform/shops", world.admin).status_code == 200


@pytest.mark.parametrize("suffix", LOT2_PATHS)
def test_lot_2_routes_do_not_exist_yet(world: World, suffix: str) -> None:
    for method in ("GET", "POST"):
        response = world.a.call(method, suffix, world.a.owner, json={})
        assert (response.status_code, response.json()["error"]["code"]) == (404, "NOT_FOUND")
