"""Portée et vue d'une créance pour l'acteur (TR-05, RG-D01 ; matrice M18 à M22).

| Rôle | Créances | Versement | Annuler, perte, ancienne | Pièces d'identité |
| --- | --- | --- | --- | --- |
| Propriétaire | toutes | oui | oui | oui |
| Vendeur | **siennes** = vendeur responsable (Q-21) | siennes | non (403) | siennes |
| Comptable, chauffeur | 403 avant toute lecture (RG-D03) | | | |

La portée « Siennes » est appliquée **dans la requête** (`responsible`) ; la créance d'un
autre vendeur → 404 (pas de fuite d'existence). Les pièces d'identité des garants ne sont
montrées qu'au propriétaire et au vendeur responsable (UC-CRE-07, SEC-N06).
"""

from dataclasses import dataclass
from datetime import date

from app.application.ports.repository import not_found
from app.application.ports.uow import UnitOfWork
from app.application.receivables.ports import ReceivableRepository
from app.application.sales.ports import CustomerRepository
from app.application.security.access import OwnScope
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.security.roles import Role
from app.domain.receivables.ids import ReceivableId
from app.domain.receivables.receivable import Receivable
from app.domain.receivables.values import SeniorityBand, seniority_band
from app.domain.sales.customer import Customer
from app.domain.shared.ids import UserId


def responsible_scope(policy: Policy, actor: Actor, permission: Permission) -> UserId | None:
    """Vendeur responsable imposé à la requête (portée OWN), sinon `None` (toutes)."""
    scope = policy.scope_filter(actor, permission)
    return scope.user_id if isinstance(scope, OwnScope) else None


def visible_receivable(
    uow: UnitOfWork, receivable_id: ReceivableId, responsible: UserId | None
) -> Receivable:
    receivable = ReceivableRepository.within(uow).get(receivable_id)
    require_in_scope(receivable, responsible)
    return receivable


def require_in_scope(receivable: Receivable, responsible: UserId | None) -> None:
    if responsible is not None and receivable.responsible_seller_id != responsible:
        raise not_found(receivable.id)


@dataclass(frozen=True, slots=True)
class ReceivableView:
    receivable: Receivable
    customer: Customer
    today: date
    show_id_docs: bool
    """Pièces d'identité des garants visibles (propriétaire, vendeur responsable)."""
    manageable: bool
    """Annuler un versement, passer en perte, changer le responsable (propriétaire)."""

    @property
    def seniority(self) -> int:
        return self.receivable.seniority(self.today)

    @property
    def band(self) -> SeniorityBand:
        return seniority_band(self.seniority)


def view_of(uow: UnitOfWork, actor: Actor, receivable: Receivable, today: date) -> ReceivableView:
    customer = CustomerRepository.within(uow).get(receivable.customer_id)
    owner = actor.role is Role.OWNER
    return ReceivableView(
        receivable=receivable,
        customer=customer,
        today=today,
        show_id_docs=owner or receivable.responsible_seller_id == actor.user_id,
        manageable=owner,
    )
