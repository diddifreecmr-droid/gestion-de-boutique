"""Vue d'une vente pour l'acteur (TR-05) : la vente et ce que le présentateur peut en montrer.

| Rôle | Ventes | Coûts figés et marges | Modifier, annuler |
| --- | --- | --- | --- |
| Propriétaire | toutes | oui (`COST_READ`) | oui |
| Vendeur | les siennes (OWN, filtré dans la requête) | **jamais** (RG-D02) | non (signaler) |
| Comptable, chauffeur | 403 avant toute lecture (RG-D03) | | |

`show_costs` est le **seul** interrupteur que lit le présentateur : faux, les clés
`frozen_last_cost`, `frozen_wac`, `margin`, `margin_wac` ne sont pas posées (SEC-N01).
"""

from dataclasses import dataclass

from app.application.sales.checks import SaleWarning
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.security.roles import Role
from app.domain.sales.error_report import ErrorReport
from app.domain.sales.sale import Sale
from app.domain.sales.values import SaleStatus


@dataclass(frozen=True, slots=True)
class SaleView:
    sale: Sale
    show_costs: bool
    editable: bool
    """Modification et annulation possibles par cet acteur (propriétaire, vente valide)."""
    warnings: tuple[SaleWarning, ...] = ()
    reports: tuple[ErrorReport, ...] = ()


def view_of(
    policy: Policy,
    actor: Actor,
    sale: Sale,
    *,
    warnings: tuple[SaleWarning, ...] = (),
    reports: tuple[ErrorReport, ...] = (),
) -> SaleView:
    valid = sale.status is SaleStatus.VALID
    return SaleView(
        sale=sale,
        show_costs=policy.can_read_field(actor, Permission.COST_READ),
        editable=valid and actor.role is Role.OWNER,
        warnings=warnings,
        reports=reports,
    )
