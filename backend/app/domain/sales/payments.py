"""Paiements notés à la vente (CDC § 20.4 « Paiement de vente », RG-T19, RG-T20).

L'application n'encaisse rien : chaque paiement note un montant (> 0), un mode de paiement de
la boutique et une référence facultative. Nature **calculée** : « Comptant » pour une vente au
comptant, « Acompte » pour une vente à crédit. Plusieurs modes possibles (300 000 Espèces +
200 000 Orange Money) ; leur somme ne dépasse jamais le total (`rules.check_payments`).
"""

from dataclasses import dataclass
from enum import StrEnum

from app.domain.sales.ids import SalePaymentId
from app.domain.shared.errors import InvalidAmount
from app.domain.shared.money import Money
from app.domain.shops.ids import PaymentModeId
from app.domain.shops.values import clean_optional

REFERENCE_MAX_LENGTH = 64
MAX_PAYMENTS = 10


class PaymentNature(StrEnum):
    CASH = "cash"  # Comptant
    DEPOSIT = "deposit"  # Acompte


@dataclass(frozen=True, slots=True, kw_only=True)
class SalePayment:
    id: SalePaymentId
    mode_id: PaymentModeId
    amount: Money
    reference: str | None = None

    def __post_init__(self) -> None:
        if self.amount.amount <= 0:
            msg = "Le montant d'un paiement doit être supérieur à 0"
            raise InvalidAmount(msg, details={"field": "payments.amount"})
        if not isinstance(self.mode_id, PaymentModeId):
            msg = "SalePayment.mode_id doit être un PaymentModeId"
            raise TypeError(msg)
        ref = clean_optional(self.reference, "payments.reference", max_length=REFERENCE_MAX_LENGTH)
        object.__setattr__(self, "reference", ref)
