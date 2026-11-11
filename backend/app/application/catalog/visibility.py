"""Qui voit quels prix d'un article (TR-05, RG-D02, CDC § 4.2) — **seul** endroit à changer.

| Rôle | Prix de base | Prix minimum | Dernier coût, CMP | Historique des prix |
| --- | --- | --- | --- | --- |
| Propriétaire | oui | oui | oui | oui |
| Vendeur | oui | oui (voir ci-dessous) | **jamais** (RG-D02) | non |
| Comptable | non (Q-14, `role_matrix.py`) | non | oui | non |
| Chauffeur | aucun accès au catalogue (`STOCK_READ` refusé) | | | |

**Prix minimum du vendeur : décision en attente du client.** Il est aujourd'hui montré à qui lit
les prix de vente (`SELLING_PRICE_READ`), donc au vendeur. Pour le lui cacher, passer
`MIN_PRICE_HIDDEN_FROM_SELLER` à `True` : rien d'autre à modifier, le présentateur ne lit que
`CatalogVisibility` (le contrôle de la vente sous le minimum, T16, reste côté serveur).
"""

from dataclasses import dataclass

from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.security.roles import Role

READ_PERMISSION = Permission.STOCK_READ
"""Consulter le catalogue : « Voir le stock disponible » (Tout | Lecture | Tout | —)."""

MIN_PRICE_HIDDEN_FROM_SELLER = False
"""Décision en attente du client : cacher le prix minimum au vendeur ? (aujourd'hui : non)."""


@dataclass(frozen=True, slots=True, kw_only=True)
class CatalogVisibility:
    selling_prices: bool
    min_prices: bool
    costs: bool
    price_history: bool


def visibility_for(policy: Policy, actor: Actor) -> CatalogVisibility:
    selling = policy.can_read_field(actor, Permission.SELLING_PRICE_READ)
    hidden = MIN_PRICE_HIDDEN_FROM_SELLER and actor.role is Role.SELLER
    return CatalogVisibility(
        selling_prices=selling,
        min_prices=selling and not hidden,
        costs=policy.can_read_field(actor, Permission.COST_READ),
        price_history=selling and policy.can_read_field(actor, Permission.AUDIT_READ),
    )
