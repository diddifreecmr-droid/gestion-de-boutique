"""Erreurs métier du stock (T14) → HTTP 422 sauf mention (`interface/http/errors.py`).

| Erreur | Code | Cas |
| --- | --- | --- |
| `StockInsufficient` | `STOCK_INSUFFICIENT` | RG-T17 : sortie en ligne, stock négatif |
| `InventoryAlreadyOpen` | `INVENTORY_IN_PROGRESS` | UC-STK-07 : un seul en cours par lieu |
| `MovementAlreadyReversed` | `INVALID_STATE_TRANSITION` | annuler deux fois un même mouvement |
| `ReasonRequired` | `VALIDATION_ERROR` (400) | écart d'inventaire sans motif (INV-03) |

`StockInsufficient.details` : `available` (chaîne décimale, stock vendable du lieu) et
`other_locations` (`[{location_id, location_name, available}]`, lieux **actifs** qui ont du
stock vendable de cet article, décision Q-43 : lieux à 0 exclus, entrepôts inclus). Aucune
donnée de coût : l'erreur est montrée au vendeur (SEC-N01).
"""

from collections.abc import Sequence
from dataclasses import dataclass

from app.domain.shared.errors import DomainError, InvalidStateTransition, ValidationFailed
from app.domain.shared.quantity import Quantity


@dataclass(frozen=True, slots=True)
class OtherLocation:
    location_id: str
    location_name: str
    available: Quantity


class StockInsufficient(DomainError):
    code = "STOCK_INSUFFICIENT"

    def __init__(
        self,
        *,
        article_id: str,
        location_id: str,
        available: Quantity,
        requested: Quantity,
        other_locations: Sequence[OtherLocation] = (),
    ) -> None:
        super().__init__(
            "Stock insuffisant dans ce lieu",
            details={
                "article_id": article_id,
                "location_id": location_id,
                "available": str(available),
                "requested": str(requested),
                "other_locations": [
                    {
                        "location_id": other.location_id,
                        "location_name": other.location_name,
                        "available": str(other.available),
                    }
                    for other in other_locations
                ],
            },
        )


class InventoryAlreadyOpen(DomainError):
    code = "INVENTORY_IN_PROGRESS"

    def __init__(self, location_id: str, inventory_id: str | None = None) -> None:
        super().__init__(
            "Un inventaire est déjà en cours dans ce lieu",
            details={"location_id": location_id, "inventory_id": inventory_id},
        )


class MovementAlreadyReversed(InvalidStateTransition):
    def __init__(self, movement_id: str) -> None:
        super().__init__("Ce mouvement est déjà annulé", details={"movement_id": movement_id})


class ReasonRequired(ValidationFailed):
    def __init__(self, article_ids: Sequence[str]) -> None:
        super().__init__(
            "Un motif est obligatoire pour chaque écart (ou un motif global)",
            details={"field": "reasons", "articles": list(article_ids)},
        )
