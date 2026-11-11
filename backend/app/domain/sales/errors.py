"""Erreurs métier du module Ventes (T16a) → HTTP 422 sauf mention (`interface/http/errors.py`).

| Erreur | Code | HTTP | Cas |
| --- | --- | --- | --- |
| `PriceBelowMinimum` | `PRICE_BELOW_MINIMUM` | 422 | vendeur sous le minimum (UC-VEN-03) |
| `CreditLimitExceeded` | `CREDIT_LIMIT_EXCEEDED` | 422 | vendeur au-delà du plafond (UC-VEN-02) |
| `SaleOverpayment` | `OVERPAYMENT` | 422 | paiements > total (RG-T20) |
| `PaymentIncomplete` | `PAYMENT_INCOMPLETE` | 422 | comptant non intégralement payé (Q-12) |
| `LocationNotAllowed` | `LOCATION_NOT_ALLOWED` | 422 | vendeur hors de son lieu habituel (Q-36) |
| `LineChangeRefused` | `LINE_CHANGE_NOT_ALLOWED` | 422 | modifier article ou quantité (UC-VEN-07) |
| `ChassisAlreadySold` | `DUPLICATE` | 409 | châssis d'une vente non annulée (RG-M01) |
| `CustomerRequired` | `VALIDATION_ERROR` | 400 | crédit sans client (H20) |

Aucun détail ne contient de coût ni de marge : ces erreurs sont montrées au vendeur (SEC-N01).
"""

from app.domain.shared.errors import DomainError, Duplicate, ValidationFailed
from app.domain.shared.money import Money


class PriceBelowMinimum(DomainError):
    """`details` : `article_id`, `line` (position, 1 = première), `min_price`,
    `request_required` (toujours vrai : seul l'accord du propriétaire débloque, T16b)."""

    code = "PRICE_BELOW_MINIMUM"

    def __init__(self, *, article_id: str, line: int, min_price: Money) -> None:
        super().__init__(
            "Prix inférieur au minimum : validation du propriétaire nécessaire",
            details={
                "article_id": article_id,
                "line": line,
                "min_price": min_price.amount,
                "request_required": True,
            },
        )


class CreditLimitExceeded(DomainError):
    code = "CREDIT_LIMIT_EXCEEDED"

    def __init__(self, *, customer_id: str, limit: Money, due_before: Money, due_after: Money):
        super().__init__(
            "La nouvelle dette dépasse le plafond de crédit du client",
            details={
                "customer_id": customer_id,
                "limit": limit.amount,
                "due_before": due_before.amount,
                "due_after": due_after.amount,
            },
        )


class SaleOverpayment(DomainError):
    code = "OVERPAYMENT"

    def __init__(self, *, total: Money, paid: Money) -> None:
        super().__init__(
            "Le total des paiements dépasse le montant de la vente",
            details={"total": total.amount, "paid": paid.amount},
        )


class PaymentIncomplete(DomainError):
    code = "PAYMENT_INCOMPLETE"

    def __init__(self, *, total: Money, paid: Money) -> None:
        super().__init__(
            "Une vente au comptant est payée en entier : complétez les paiements ou passez "
            "« À crédit »",
            details={
                "total": total.amount,
                "paid": paid.amount,
                "remaining": (total - paid).amount,
            },
        )


class LocationNotAllowed(DomainError):
    code = "LOCATION_NOT_ALLOWED"

    def __init__(self, location_id: str, allowed: str | None) -> None:
        super().__init__(
            "Un vendeur vend depuis son lieu de vente habituel",
            details={"location_id": location_id, "allowed_location_id": allowed},
        )


class LineChangeRefused(DomainError):
    code = "LINE_CHANGE_NOT_ALLOWED"

    def __init__(self, field: str) -> None:
        super().__init__(
            "Changer l'article ou la quantité passe par un retour ou une annulation",
            details={"field": field},
        )


class ChassisAlreadySold(Duplicate):
    """`details` : `field` (`chassis_number`), `value` (saisie nettoyée), `sale_number` (vente
    qui le porte, `None` quand le doublon est dans la même vente), `constraint`."""

    def __init__(self, value: str, sale_number: str | None) -> None:
        super().__init__(
            "Ce numéro de châssis a déjà été vendu",
            details={
                "field": "chassis_number",
                "value": value,
                "sale_number": sale_number,
                "constraint": "sold_chassis_active",
            },
        )


class CustomerRequired(ValidationFailed):
    def __init__(self) -> None:
        super().__init__(
            "Client obligatoire (nom et téléphone) pour une vente à crédit",
            details={"field": "customer"},
        )
