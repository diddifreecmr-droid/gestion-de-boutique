"""Qui voit quoi dans les écrans de stock (TR-05, RG-D02, RG-D03) — seul endroit à changer.

| Rôle | Quantités | Prix de base | Coûts (dernier coût, CMP, valeur) | N° de vente lié |
| --- | --- | --- | --- | --- |
| Propriétaire | oui | oui | oui | oui |
| Comptable | oui | non (Q-14) | oui | **non** (RG-D03, Q-39 retenue : type seul) |
| Vendeur | oui | oui | **jamais** | — (pas d'historique) |
| Chauffeur | aucun accès (`STOCK_READ` refusé) | | | |
"""

from dataclasses import dataclass

from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy


@dataclass(frozen=True, slots=True, kw_only=True)
class StockVisibility:
    costs: bool
    selling_prices: bool
    sales_documents: bool


def stock_visibility(policy: Policy, actor: Actor) -> StockVisibility:
    return StockVisibility(
        costs=policy.can_read_field(actor, Permission.COST_READ),
        selling_prices=policy.can_read_field(actor, Permission.SELLING_PRICE_READ),
        sales_documents=policy.can_read_field(actor, Permission.SALES_DATA_READ),
    )
