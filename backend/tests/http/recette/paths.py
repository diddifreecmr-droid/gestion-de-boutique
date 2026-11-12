"""Chemins et corps des requêtes de recette : paramètres de chemin remplis depuis une `Side`."""

import re
from collections.abc import Callable, Mapping
from itertools import count
from typing import Any

from tests.http.recette.world import Side

Body = Callable[[Side], dict[str, Any] | None]
_n = count(1)

# Paramètre de chemin → clé de `Side.ids` (ou de `Side.users` pour `user_id`).
PARAMS = {
    "article_id": "article", "sale_id": "sale_seller", "receivable_id": "receivable_seller",
    "customer_id": "customer_seller", "purchase_id": "purchase", "supplier_id": "supplier",
    "expense_id": "expense", "installment_id": "installment", "location_id": "garoua",
    "mode_id": "cash", "category_id": "fuel", "inventory_id": "inventory",
    "report_id": "report", "request_id": "price_request", "reminder_id": "reminder",
    "alert_id": "alert", "entity_id": "sale_seller", "user_id": "seller2",
}  # fmt: skip
CONSTANTS = {"metric": "sales", "entity_type": "sale"}
_PARAM = re.compile(r"\{(\w+)\}")


def unique(prefix: str) -> str:
    return f"{prefix} {next(_n)}"


def phone() -> str:
    return f"65{next(_n):07d}"


def url(side: Side, template: str, overrides: Mapping[str, str] | None = None) -> str:
    """Chemin (sans `/shops/{id}`) ; `overrides` : paramètre → autre clé de `side.ids`."""
    chosen = {**PARAMS, **(overrides or {})}

    def fill(match: re.Match[str]) -> str:
        name = match.group(1)
        if name in CONSTANTS:
            return CONSTANTS[name]
        key = chosen[name]
        return side.users[key] if name == "user_id" else side.ids[key]

    return _PARAM.sub(fill, template)


def versioned(path: str, **fields: Any) -> Body:
    """Corps `{version, …}` : la version est relue chez le propriétaire au moment de l'envoi."""

    def body(side: Side) -> dict[str, Any]:
        return {"version": side.version(url(side, path)), **fields}

    return body


def listed(path: str, key: str, **fields: Any) -> Body:
    """Comme `versioned`, pour un objet sans lecture unitaire : version lue dans la liste."""

    def body(side: Side) -> dict[str, Any]:
        found = side.ok("GET", path, side.owner)
        items = found["items"] if isinstance(found, dict) else found
        version = next(
            i["version"] for i in items if side.ids[key] in (i.get("id"), i.get("user_id"))
        )
        return {"version": version, **fields}

    return body
