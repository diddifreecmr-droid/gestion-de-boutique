"""Critère A7 / AUD-05, AUD-06 (RG-T01, RG-T02) : toute écriture réussie laisse une trace.

Une boutique remplie ; chaque route d'écriture de `ROUTES` est appelée par le propriétaire,
les actions destructrices (annulations, archivage, perte…) en dernier. Pour chaque réponse
2xx, le journal de la boutique doit compter **au moins une** entrée de plus. Seules
exceptions, qui ne changent pas l'état métier : marquer une alerte lue, un envoi `/sync` vide
(une modification sans aucun changement n'est pas journalisée : les corps changent vraiment).
L'OpenAPI n'expose aucune route `DELETE` métier.
"""

from typing import Any

from tests.http.recette.paths import url
from tests.http.recette.routes import ROUTES
from tests.http.recette.test_rights_matrix_http import denied_count
from tests.http.recette.world import Side, World

NOT_JOURNALED = {"POST /alerts/{alert_id}/read", "POST /sync"}
LAST = (
    "POST /sales/{sale_id}/returns", "POST /sales/{sale_id}/cancel",
    "POST /purchases/{purchase_id}/cancel", "POST /expenses/{expense_id}/cancel",
    "POST /installments/{installment_id}/cancel", "POST /receivables/{receivable_id}/write-off",
    "POST /articles/{article_id}/archive", "POST /tags/merge",
    "POST /inventories/{inventory_id}/abandon", "POST /members/{user_id}/revoke-devices",
    "POST /members/{user_id}/reset-pin", "DELETE /admin-access",
)  # fmt: skip


def journal_size(side: Side) -> int:
    total, cursor = 0, None
    while True:
        params: dict[str, Any] = {"limit": 200} | ({"cursor": cursor} if cursor else {})
        page = side.ok("GET", "/audit", side.owner, params=params)
        total += len(page["items"])
        cursor = page["next_cursor"]
        if cursor is None:
            return total


def test_every_successful_write_is_journaled(world: World) -> None:
    side = world.a
    writes = [r for r in ROUTES if not r.startswith("GET ")]
    ordered = [r for r in writes if r not in LAST] + list(LAST)
    silent, exercised = [], []
    for route in ordered:
        method, template = route.split(" ", 1)
        factory = ROUTES[route]
        before = journal_size(side)
        response = side.call(method, url(side, template), side.owner,
                             json=factory(side) if factory else None)  # fmt: skip
        if response.status_code >= 300:
            continue
        exercised.append(route)
        if journal_size(side) <= before and route not in NOT_JOURNALED:
            silent.append(route)
    assert silent == [], silent
    assert len(exercised) >= len(writes) - 8, sorted(set(writes) - set(exercised))
    assert denied_count(side) == 0


def test_no_business_delete_route(world: World) -> None:
    paths = world.api.client.app.openapi()["paths"]  # type: ignore[attr-defined]
    deletes = sorted(p for p, ops in paths.items() if "delete" in ops)
    # Seule exception : le propriétaire **retire** la délégation de l'administrateur (§ 8.3).
    assert deletes == ["/api/v1/shops/{shop_id}/admin-access"]
