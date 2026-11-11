"""Paiements fournisseur et statut de paiement d'un achat (UC-ACH-06, CDC § 20.3).

Simple repère (pas de gestion des dettes fournisseur en V1, CDC § 22) : date, montant > 0,
mode de paiement de la boutique, référence facultative. Le total payé ne dépasse jamais le
total de l'achat (`Overpayment`, 422). Statut calculé : « À payer » (rien de payé),
« Payé en partie », « Payé » (payé = total ; un achat à 0 FCFA est « Payé »).
"""

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from app.domain.purchasing.ids import SupplierPaymentId
from app.domain.shared.business_day import require_aware
from app.domain.shared.errors import InvalidAmount
from app.domain.shared.ids import UserId
from app.domain.shared.money import Money
from app.domain.shops.ids import PaymentModeId
from app.domain.shops.values import clean_optional

REFERENCE_MAX_LENGTH = 64


class PaymentStatus(StrEnum):
    TO_PAY = "to_pay"  # À payer
    PARTIALLY_PAID = "partially_paid"  # Payé en partie
    PAID = "paid"  # Payé


@dataclass(frozen=True, slots=True, kw_only=True)
class SupplierPayment:
    id: SupplierPaymentId
    paid_on: date
    amount: Money
    mode_id: PaymentModeId
    recorded_at: datetime
    recorded_by: UserId
    reference: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.paid_on, datetime) or not isinstance(self.paid_on, date):
            msg = "SupplierPayment.paid_on doit être une date"
            raise TypeError(msg)
        if self.amount.amount <= 0:
            msg = "Le montant d'un paiement doit être supérieur à 0"
            raise InvalidAmount(msg, details={"field": "amount"})
        if not isinstance(self.mode_id, PaymentModeId):
            msg = "SupplierPayment.mode_id doit être un PaymentModeId"
            raise TypeError(msg)
        object.__setattr__(self, "recorded_at", require_aware(self.recorded_at))
        ref = clean_optional(self.reference, "reference", max_length=REFERENCE_MAX_LENGTH)
        object.__setattr__(self, "reference", ref)


def payment_status(total: Money, paid: Money) -> PaymentStatus:
    if paid >= total:
        return PaymentStatus.PAID
    return PaymentStatus.TO_PAY if paid.amount == 0 else PaymentStatus.PARTIALLY_PAID
