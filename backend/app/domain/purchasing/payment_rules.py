"""Noter un paiement fournisseur sur un achat (UC-ACH-06 ; recette PUR-12, ERR-OVR-05).

Fonction du domaine qui fait évoluer l'agrégat `Purchase` : achat valide, total payé ≤ total
(`Overpayment` porte le reste à payer), événement journalisé. Un identifiant de paiement déjà
noté renvoie `False` sans rien changer (rejeu idempotent).
"""

from app.domain.audit.values import Performer
from app.domain.purchasing.errors import Overpayment
from app.domain.purchasing.events import SupplierPaymentRecorded
from app.domain.purchasing.payments import SupplierPayment
from app.domain.purchasing.purchase import Purchase


def add_payment(purchase: Purchase, payment: SupplierPayment, *, performer: Performer) -> bool:
    if any(existing.id == payment.id for existing in purchase.payments):
        return False
    purchase.require_valid()
    if purchase.paid + payment.amount > purchase.total:
        raise Overpayment(total=purchase.total, paid=purchase.paid)
    purchase.payments = (*purchase.payments, payment)
    purchase.events.record(
        SupplierPaymentRecorded(
            shop_id=purchase.shop_id,
            occurred_at=payment.recorded_at,
            performer=performer,
            entity=purchase.entity,
            summary=f"Paiement de {payment.amount} noté sur l'achat {purchase.number}",
        )
    )
    return True
