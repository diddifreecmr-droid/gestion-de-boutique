"""Modules par boutique (décision client specs § 15.1) : chaque route de boutique déclare son
module (`x-module`) ; module éteint → 403 `MODULE_DISABLED` sur **toutes** ses routes, après
l'appartenance (un non-membre garde 404) et avant le corps ; les autres modules marchent, la
boutique voisine n'est pas touchée et les données réapparaissent à la réactivation.
"""

from typing import Any

import pytest

from app.domain.profiles.modules import ALL_MODULES, MANDATORY_MODULES, Module
from tests.http.recette.paths import url
from tests.http.recette.routes import ROUTES
from tests.http.recette.world import Side, World

PREFIX = "/api/v1/shops/{shop_id}"
# Modules facultatifs qui ont des routes au Lot 1 (transferts, transport, import : aucune).
GATED = (Module.PURCHASES, Module.RECEIVABLES, Module.EXPENSES, Module.DASHBOARD)


def route_modules(world: World) -> dict[str, Module]:
    """`"METHODE /chemin"` (sans `/shops/{shop_id}`) → module déclaré dans l'OpenAPI."""
    paths = world.api.client.app.openapi()["paths"]  # type: ignore[attr-defined]
    return {
        f"{method.upper()} {path.removeprefix(PREFIX)}": Module(operation["x-module"])
        for path, operations in paths.items()
        if path.startswith(f"{PREFIX}/")
        for method, operation in operations.items()
        if "x-module" in operation
    }


def set_modules(world: World, side: Side, modules: frozenset[Module]) -> dict[str, Any]:
    body = {"modules": sorted(m.value for m in modules)}
    response = world.api.call("PATCH", f"/platform/shops/{side.id}", world.admin, json=body)
    assert response.status_code == 200, response.text
    found: dict[str, Any] = response.json()
    return found


def send(side: Side, route: str, who: Any, *, body: bool = True) -> Any:
    method, template = route.split(" ", 1)
    factory = ROUTES[route]
    payload = factory(side) if factory and body else None
    return side.api.call(method, f"/shops/{side.id}{url(side, template)}", who, json=payload)


def test_every_shop_route_of_the_openapi_declares_its_module(world: World) -> None:
    declared = route_modules(world)
    assert set(declared) == set(ROUTES)  # aucune route de boutique sans module
    assert {route for route, module in declared.items() if module is Module.RECEIVABLES} >= {
        "POST /receivables/{receivable_id}/guarantors",
        "POST /customers/{customer_id}/installments",
        "GET /customers/{customer_id}/statement",
    }
    assert declared["GET /home"] is declared["GET /alerts"] is Module.CORE
    assert declared["GET /dashboard"] is Module.DASHBOARD
    assert declared["POST /tags/merge"] is Module.EXPENSES
    assert declared["POST /suppliers"] is Module.PURCHASES
    assert declared["POST /adjustments"] is Module.CATALOG


@pytest.mark.parametrize("module", GATED)
def test_a_disabled_module_closes_all_its_routes_and_only_them(
    world: World, module: Module
) -> None:
    modules = route_modules(world)
    own = [route for route, m in modules.items() if m is module]
    reads = [r for r, m in modules.items() if m is not module and r.startswith("GET ")]
    before = {r: send(world.a, r, world.a.owner).json() for r in own if r.startswith("GET ")}
    set_modules(world, world.a, ALL_MODULES - {module})
    gaps = []
    for route in own:
        response = send(world.a, route, world.a.owner, body=False)  # corps absent : 403 d'abord
        error = response.json().get("error", {})
        if (response.status_code, error.get("code"), error.get("details")) != (
            403, "MODULE_DISABLED", {"module": module.value}
        ):  # fmt: skip
            gaps.append(f"{route} : {response.status_code} {response.text[:80]}")
        if (
            send(world.a, route, world.b.owner, body=False).status_code != 404
        ):  # non-membre : 404 d'abord
            gaps.append(f"{route} : non-membre")
    for route in reads:  # `GET /offline-snapshot` : hors offre (FEATURE_DISABLED), pas module
        response = send(world.a, route, world.a.owner)
        offer = response.status_code == 403 and "FEATURE_DISABLED" in response.text
        if response.status_code != 200 and not offer:
            gaps.append(f"{route} (autre module) : {response.status_code}")
    for route in own:  # la boutique voisine garde le module
        if route.startswith("GET ") and send(world.b, route, world.b.owner).status_code != 200:
            gaps.append(f"{route} (boutique B)")
    assert gaps == []
    set_modules(world, world.a, ALL_MODULES)
    after = {r: send(world.a, r, world.a.owner).json() for r in before}
    assert after == before  # données gardées, réapparues à la réactivation


def test_platform_patch_refuses_invalid_combinations(world: World) -> None:
    path = f"/platform/shops/{world.a.id}"

    def patch(modules: frozenset[Module]) -> Any:
        body = {"modules": sorted(m.value for m in modules)}
        return world.api.call("PATCH", path, world.admin, json=body)

    for mandatory in sorted(MANDATORY_MODULES):
        refused = patch(ALL_MODULES - {mandatory})
        assert refused.status_code == 422, refused.text
        assert refused.json()["error"]["code"] == "MODULE_MANDATORY"
        assert refused.json()["error"]["details"] == {"module": mandatory.value}
    refused = patch(ALL_MODULES - {Module.TRANSFERS})
    assert refused.status_code == 422
    assert refused.json()["error"] == {
        "code": "MODULE_DEPENDENCY",
        "message": refused.json()["error"]["message"],
        "details": {"module": "transport", "requires": "transfers"},
    }
    shop = world.api.call("GET", path, world.admin).json()
    assert set(shop["enabled_modules"]) == ALL_MODULES  # rien n'a changé
    minimal = patch(MANDATORY_MODULES)
    assert minimal.status_code == 200
    assert set(minimal.json()["enabled_modules"]) == MANDATORY_MODULES
    profile = world.a.ok("GET", "/profile", world.a.owner)
    assert set(profile["enabled_modules"]) == MANDATORY_MODULES
    entries = [e for top in profile["menu"] for e in [top, *top.get("children", [])]]
    assert {e["module"] for e in entries} <= {m.value for m in MANDATORY_MODULES}
