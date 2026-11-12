"""Matrice des droits § 4.2 (recette § 3.1, SEC-M01 à M30) en requêtes HTTP réelles.

Chaque cellule : une route de `ROUTES`, puis 4 lettres dans l'ordre Propriétaire, Vendeur,
Comptable, Chauffeur — `Y` autorisé (2xx, ou refus **métier** 409/422 qui prouve que le droit
a été accordé), `-` 403 `FORBIDDEN`, `n` 404 (objet hors de sa portée « Siens »),
`f` 403 `FEATURE_DISABLED` (hors-ligne inactif en V1).

Écarts assumés avec le tableau de la recette (décisions specs § 15.1) : M16, vendeur sous le
minimum → **201 avec avertissement** (pas d'accord par défaut) ; M17 exige donc le réglage
« accord du propriétaire » activé (préparé par la ligne).
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from tests.http.recette.paths import Body
from tests.http.recette.routes_trade import cash_sale
from tests.http.recette.world import HJ, Side, approval

ROLES = ("owner", "seller", "accountant", "driver")


@dataclass(frozen=True)
class Cell:
    route: str
    letters: str
    overrides: Mapping[str, str] = field(default_factory=dict)
    body: Body | None = None  # remplace le corps par défaut de la route


def _priced_article(side: Side) -> dict[str, Any]:
    return {"fields": {**HJ["fields"], "model": "HJ150"}, "base_price": 900_000}


def _below_minimum(side: Side) -> dict[str, Any]:
    return cash_sale(side, 719_999)


V2 = {"sale_id": "sale_seller2"}
ROWS: Mapping[str, tuple[Cell, ...]] = {
    "M01": tuple(Cell(r, "Y---") for r in (
        "GET /members", "POST /members", "PATCH /members/{user_id}",
        "POST /members/{user_id}/reset-pin", "POST /members/{user_id}/revoke-devices",
        "POST /members/{user_id}/unlock", "PATCH /settings", "POST /payment-modes",
        "PATCH /payment-modes/{mode_id}")),
    "M02": (Cell("POST /locations", "Y---"), Cell("PATCH /locations/{location_id}", "Y---")),
    "M03": (Cell("GET /locations", "Y-Y-"),),
    "M04": (Cell("POST /articles", "Y-Y-"), Cell("PATCH /articles/{article_id}", "Y-Y-")),
    "M05": (Cell("PUT /articles/{article_id}/prices", "Y---"),
            Cell("POST /articles", "Y---", body=_priced_article)),
    "M06": (Cell("POST /articles/{article_id}/archive", "Y---"),),
    "M07": (Cell("GET /stock", "YYY-"), Cell("GET /articles", "YYY-")),
    "M08": tuple(Cell(r, "Y-Y-") for r in (
        "GET /stock/value", "GET /articles/{article_id}/movements", "GET /stock/damaged")),
    "M09": tuple(Cell(r, "Y-Y-") for r in (
        "POST /adjustments", "POST /inventories", "PUT /inventories/{inventory_id}/counts",
        "POST /inventories/{inventory_id}/validate")),
    "M10": tuple(Cell(r, "Y-Y-") for r in (
        "GET /suppliers", "POST /suppliers", "GET /purchases", "POST /purchases",
        "PATCH /purchases/{purchase_id}", "POST /purchases/{purchase_id}/payments")),
    "M11": (Cell("POST /purchases/{purchase_id}/cancel", "Y---"),),
    "M12": (Cell("POST /sales", "YY--"),),
    "M13": (Cell("GET /sales", "YY--"), Cell("GET /sales/{sale_id}", "Yn--", V2)),
    "M14": tuple(Cell(r, "Y---") for r in (
        "PATCH /sales/{sale_id}", "POST /sales/{sale_id}/returns", "POST /sales/{sale_id}/cancel")),
    "M15": (Cell("POST /sales/{sale_id}/error-reports", "YY--"),),
    "M16": (Cell("POST /sales", "YY--", body=_below_minimum),),
    "M17": (Cell("POST /price-requests", "YY--"),
            Cell("POST /price-requests/{request_id}/decision", "Y---")),
    "M18": (Cell("GET /receivables", "YY--"), Cell("POST /receivables", "Y---")),
    "M19": (Cell("POST /receivables/{receivable_id}/installments", "YY--"),
            Cell("POST /receivables/{receivable_id}/installments", "Yn--",
                 {"receivable_id": "receivable_seller2"})),
    "M20": (Cell("POST /installments/{installment_id}/cancel", "Y---"),
            Cell("POST /receivables/{receivable_id}/write-off", "Y---")),
    "M21": (Cell("POST /receivables/{receivable_id}/reminders", "YY--"),
            Cell("POST /receivables/{receivable_id}/guarantors", "YY--")),
    "M22": (*(Cell(r, "YY--") for r in (
        "GET /customers", "POST /customers", "PATCH /customers/{customer_id}",
        "GET /customers/{customer_id}/statement")),
            Cell("GET /customers/{customer_id}", "Yn--", {"customer_id": "customer_seller2"})),
    "M23": tuple(Cell(r, "Y-Y-") for r in (
        "GET /expenses", "POST /expenses", "PATCH /expenses/{expense_id}",
        "POST /expenses/{expense_id}/cancel")),
    "M24": (Cell("POST /expense-categories", "Y---"),
            Cell("PATCH /expense-categories/{category_id}", "Y---"),
            Cell("GET /tags", "Y-Y-"), Cell("POST /tags/merge", "Y---")),
    "M25": (Cell("GET /dashboard", "Y---"), Cell("GET /dashboard/details/{metric}", "Y---")),
    "M26": (Cell("GET /home", "YYYY"),),
    "M27": tuple(Cell(r, "Y---") for r in (
        "GET /audit", "GET /audit/entities/{entity_type}/{entity_id}",
        "GET /audit/users/{user_id}")),
    "M28": (Cell("GET /profile", "YYYY"), Cell("GET /alerts", "YYYY")),
    "M30": (Cell("POST /sync", "ffff"), Cell("GET /offline-snapshot", "ffff")),
}  # fmt: skip

# Préparation propre à une ligne (avant toute requête).
SETUP: Mapping[str, Callable[[Side], None]] = {"M17": lambda side: approval(side, True)}

# Lignes § 4.2 hors Lot 1 : aucune route ne doit exister sans ses droits.
LOT2_PATHS = ("/transfers", "/trucks", "/drivers", "/trips", "/payroll", "/imports")
