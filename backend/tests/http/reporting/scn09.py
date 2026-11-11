"""Données de SCN-09 (recette § 2) enregistrées par HTTP, horloge figée à chaque instant indiqué.

P1 (05/11) 10 x 510 000 et P2 (06/11) 10 x 550 000 → CMP 530 000, dernier coût 550 000 ; créance
ancienne « CA » 300 000 ouverte le 05/11. Ventes sans date fournie (date = journée de Douala).
Adaptation au modèle réel : S3 et C2 portent un client créé à la vente ; R1 est saisi par le
propriétaire (CA n'a pas de vendeur responsable) ; un rappel daté du 10/11 est posé sur C2.
"""

from datetime import UTC, datetime
from typing import Any

from app.domain.expenses.ids import ExpenseId
from app.domain.purchasing.ids import PurchaseId
from app.domain.receivables.ids import ReceivableId
from app.domain.sales.ids import SaleId
from tests.http.catalog.test_catalog_http import HJ
from tests.http.reporting.conftest import Desk


def utc(day: int, hour: int, minute: int = 0, second: int = 0) -> datetime:
    return datetime(2026, 11, day, hour, minute, second, tzinfo=UTC)


def _buy(desk: Desk, article: str, price: int) -> None:
    body = {
        "id": str(PurchaseId.new()),
        "lines": [{"article_id": article, "quantity": "10", "unit_price": price}],
    }
    desk.ok("POST", "/purchases", desk.staff("accountant"), json=body)


def _sell(
    desk: Desk, article: str, price: int, payments: list[tuple[str, int]], **extra: Any
) -> str:
    body: dict[str, Any] = {
        "id": str(SaleId.new()),
        "kind": "cash",
        "lines": [{"article_id": article, "quantity": "1", "unit_price": price}],
        "payments": [
            {"mode_id": desk.mode(mode), "amount": amount, "reference": "REF-1"}
            for mode, amount in payments
        ],
        **extra,
    }
    return str(desk.ok("POST", "/sales", desk.staff("seller"), json=body)["id"])


def _credit(desk: Desk, phone: str) -> dict[str, Any]:
    return {
        "kind": "credit",
        "customer": {"id": None, "name": f"Client {phone}", "phone": phone, "kind": "individual"},
        "credit": {"reminder_on": "2026-12-01", "terms": None, "guarantor": None},
    }


def stocked(desk: Desk) -> str:
    """Article, deux achats, créance ancienne CA ; renvoie l'identifiant de l'article."""
    article = str(desk.ok("POST", "/articles", desk.owner, json=HJ)["id"])
    _buy(desk, article, 510_000)
    desk.at(utc(6, 8))
    _buy(desk, article, 550_000)
    return article


def record_until_s4(desk: Desk) -> dict[str, str]:
    """De P1 à S4 (avant 10/11 23:00Z) ; renvoie les identifiants utiles."""
    article = stocked(desk)
    legacy = {
        "id": str(ReceivableId.new()),
        "customer": {"id": None, "name": "Ali B.", "phone": "+237699000001"},
        "amount": 300_000,
        "opened_on": "2026-11-05",
        "description": "Cahier 2026",
    }
    ca = str(desk.ok("POST", "/receivables", desk.owner, json=legacy)["id"])
    desk.at(utc(9, 22, 55))
    _sell(desk, article, 800_000, [("Espèces", 800_000)])  # S0
    desk.at(utc(9, 23, 10))
    _sell(desk, article, 780_000, [("Espèces", 500_000), ("Orange Money", 280_000)])  # S1
    desk.at(utc(10, 8))
    s2 = _sell(
        desk, article, 760_000, [("MTN Mobile Money", 200_000)], **_credit(desk, "+237690000002")
    )
    desk.ok(
        "POST",
        f"/receivables/{s2}/reminders",
        desk.staff("seller"),
        json={"remind_on": "2026-11-10"},
    )
    desk.at(utc(10, 9))
    installment = {"amount": 100_000, "mode_id": desk.mode("Espèces")}
    desk.ok("POST", f"/receivables/{ca}/installments", desk.owner, json=installment)  # R1
    desk.at(utc(10, 10))
    s3 = _sell(desk, article, 790_000, [], **_credit(desk, "+237690000003"))
    desk.at(utc(10, 11))
    desk.ok("POST", f"/sales/{s3}/cancel", desk.owner, json={"reason": "Client parti"})
    desk.at(utc(10, 14))
    fuel = {"id": str(ExpenseId.new()), "amount": 25_000, "category_id": desk.category("Carburant")}
    desk.ok("POST", "/expenses", desk.staff("accountant"), json=fuel)  # E1
    desk.at(utc(10, 14, 30))
    meal = {"amount": 10_000, "category_id": desk.category("Repas")}
    e2 = desk.ok("POST", "/expenses", desk.staff("accountant"), json=meal)["id"]
    desk.at(utc(10, 15))
    desk.ok("POST", f"/expenses/{e2}/cancel", desk.owner, json={"reason": "Doublon"})
    desk.at(utc(10, 22, 50))
    _sell(desk, article, 770_000, [("Espèces", 770_000)])  # S4
    return {"article": article, "ca": ca, "s2": s2}


def record_s5(desk: Desk, article: str) -> None:
    desk.at(utc(10, 23, 5))
    _sell(desk, article, 800_000, [("Espèces", 800_000)])  # S5
