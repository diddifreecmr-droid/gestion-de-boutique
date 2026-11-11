"""UC-VEN-09 — Lire les retours d'une vente et ce qu'il reste à rendre (`GET /sales/{id}/returns`).

Portée de `SALE_READ` : propriétaire toutes, vendeur **ses** ventes (celle d'un autre → 404),
comptable et chauffeur 403 (RG-D03). Retours du plus ancien au plus récent ; coût et marge
seulement pour qui voit les coûts (`return_views.py`).
"""

from app.application.ports.repository import not_found
from app.application.ports.uow import UnitOfWorkFactory
from app.application.sales.ports import SaleRepository
from app.application.sales.return_ports import SaleReturnRepository
from app.application.sales.return_views import SaleReturnsListing, balances_of, return_view
from app.application.security.access import OwnScope
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop
from app.domain.sales.ids import SaleId


class ListSaleReturns:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy) -> None:
        self._uow_factory = uow_factory
        self._policy = policy

    def execute(self, actor: Actor, sale_id: SaleId) -> SaleReturnsListing:
        scope = self._policy.scope_filter(actor, Permission.SALE_READ)
        with self._uow_factory(actor_shop(actor)) as uow:
            sale = SaleRepository.within(uow).get(sale_id)
            if isinstance(scope, OwnScope) and sale.seller_id != scope.user_id:
                raise not_found(sale_id)
            returns = SaleReturnRepository.within(uow).for_sale(sale.id)
        return SaleReturnsListing(
            sale=sale,
            returns=[return_view(self._policy, actor, made) for made in returns],
            balances=balances_of(sale, returns),
        )
