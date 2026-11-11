"""`ShopPlans` sur le compte commerçant : l'offre d'une boutique est celle de son compte (TR-26).

Remplace `FixedShopPlans` (T09). Lu à chaque question (aucun cache) : un changement d'offre du
compte prend effet à la requête suivante. Boutique inconnue → `NotFound` (jamais une offre
supposée).
"""

from app.application.plans.ports import ShopPlans
from app.application.shops.ports import ShopCatalog
from app.domain.plans.entitlements import PlanCode
from app.domain.shared.errors import NotFound
from app.domain.shared.ids import ShopId


class AccountShopPlans(ShopPlans):
    def __init__(self, catalog: ShopCatalog) -> None:
        self._catalog = catalog

    def plan_of(self, shop_id: ShopId) -> PlanCode:
        summary = self._catalog.find(shop_id)
        if summary is None:
            msg = "Boutique introuvable"
            raise NotFound(msg, details={"shop_id": str(shop_id)})
        return summary.plan
