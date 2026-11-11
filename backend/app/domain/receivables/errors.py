"""Erreurs métier du module Créances (T17) → HTTP 422 (`interface/http/errors.py`).

| Erreur | Code | Cas |
| --- | --- | --- |
| `ReceivableOverpayment` | `OVERPAYMENT` | versement > reste à payer (UC-CRE-03, SCN-07) |
| `AmountBelowPaid` | `AMOUNT_BELOW_PAID` | initial < déjà versé (vente modifiée) |

`AmountBelowPaid` est levée **dans la transaction de la vente** (handler `ReceivableSync`) :
la modification est refusée en entier plutôt que de laisser un reste négatif
(remboursement d'un trop-versé : hors Lot 1, à traiter par le propriétaire).
"""

from app.domain.shared.errors import DomainError
from app.domain.shared.money import Money


class ReceivableOverpayment(DomainError):
    code = "OVERPAYMENT"

    def __init__(self, *, remaining: Money, amount: Money) -> None:
        super().__init__(
            "Le versement dépasse le reste à payer",
            details={"remaining": remaining.amount, "amount": amount.amount},
        )


class AmountBelowPaid(DomainError):
    code = "AMOUNT_BELOW_PAID"

    def __init__(self, *, initial: Money, paid: Money) -> None:
        super().__init__(
            "Le nouveau montant de la créance serait inférieur à ce qui est déjà versé",
            details={"initial_amount": initial.amount, "paid": paid.amount},
        )
