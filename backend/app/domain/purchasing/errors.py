"""Erreurs métier du module Achats (T15) → HTTP 422 sauf mention (`interface/http/errors.py`).

| Erreur | Code | HTTP | Cas |
| --- | --- | --- | --- |
| `PriceGapToConfirm` | `PRICE_GAP_CONFIRMATION_REQUIRED` | 422 | prix > 30 % du dernier coût |
| `Overpayment` | `OVERPAYMENT` | 422 | total payé > total de l'achat (ERR-OVR-05) |
| `CorrectionWindowClosed` | `CORRECTION_WINDOW_CLOSED` | 422 | comptable après J+7 (PUR-07) |
| `StockAlreadyLeft` | `STOCK_ALREADY_LEFT` | 422 | correction/annulation sous le sorti |
| `ReasonRequired` | `REASON_REQUIRED` | 400 | correction ou annulation sans motif |

`PriceGapToConfirm.details.lines` : `[{line, article_id, last_cost, unit_price}]` — l'écran
affiche « Le dernier achat était à 520 000 FCFA. Confirmer 52 000 FCFA ? » puis renvoie
`confirm_price_gap: true` (UC-ACH-01). Seuls le propriétaire et le comptable y accèdent.
"""

from collections.abc import Mapping, Sequence
from datetime import date

from app.domain.shared.errors import DomainError, ValidationFailed
from app.domain.shared.money import Money
from app.domain.shared.quantity import Quantity


class PriceGapToConfirm(DomainError):
    code = "PRICE_GAP_CONFIRMATION_REQUIRED"

    def __init__(self, lines: Sequence[Mapping[str, object]]) -> None:
        super().__init__(
            "Prix très différent du dernier coût : confirmer la saisie",
            details={"lines": [dict(line) for line in lines]},
        )


class Overpayment(DomainError):
    code = "OVERPAYMENT"

    def __init__(self, *, total: Money, paid: Money) -> None:
        super().__init__(
            "Le total des paiements dépasserait le total de l'achat",
            details={
                "total": total.amount,
                "paid": paid.amount,
                "remaining": max(total.amount - paid.amount, 0),
            },
        )


class CorrectionWindowClosed(DomainError):
    code = "CORRECTION_WINDOW_CLOSED"

    def __init__(self, last_day: date) -> None:
        super().__init__(
            "Délai dépassé : seul le propriétaire peut encore corriger cet achat",
            details={"last_day": last_day.isoformat()},
        )


class StockAlreadyLeft(DomainError):
    code = "STOCK_ALREADY_LEFT"

    def __init__(
        self, *, article_id: str, location_id: str, left: Quantity, requested: Quantity
    ) -> None:
        super().__init__(
            "Une partie de cette marchandise a déjà quitté le lieu : passez par un ajustement",
            details={
                "article_id": article_id,
                "location_id": location_id,
                "left": str(left),
                "requested": str(requested),
            },
        )


class ReasonRequired(ValidationFailed):
    code = "REASON_REQUIRED"

    def __init__(self) -> None:
        super().__init__("Le motif est obligatoire", details={"field": "reason"})
