"""Vue d'un achat pour l'acteur : l'achat et ce qu'il peut encore en faire (UC-ACH-03/04).

Les achats ne sont lisibles que par le propriétaire et le comptable (`PURCHASE_READ`), qui
voient tous deux les coûts (`COST_READ`) : aucun filtrage de champ n'est nécessaire, le
vendeur et le chauffeur reçoivent 403 avant toute lecture (RG-D02).
"""

from dataclasses import dataclass
from datetime import date

from app.application.security.actor import Actor
from app.application.security.roles import Role
from app.domain.purchasing.purchase import Purchase
from app.domain.purchasing.rules import PurchaseStatus


@dataclass(frozen=True, slots=True)
class PurchaseView:
    purchase: Purchase
    editable: bool
    """Correction encore possible : achat valide, propriétaire ou comptable jusqu'à J+7."""
    cancellable: bool
    """Annulation possible par cet acteur (propriétaire, achat valide)."""


def view_of(actor: Actor, purchase: Purchase, today: date) -> PurchaseView:
    valid = purchase.status is PurchaseStatus.VALID
    owner = actor.role is Role.OWNER
    in_window = owner or today <= purchase.last_correction_day
    return PurchaseView(purchase, valid and in_window, valid and owner)
