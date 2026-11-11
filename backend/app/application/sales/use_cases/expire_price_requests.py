"""TR-19 / ERR-PRM-09 — Expirer les demandes de prix échues (tâche planifiée du worker).

Pour une boutique : chaque demande en attente, ou acceptée sans vente liée, dont l'échéance
(`expires_at`, 30 minutes) est passée à `now` passe « Expirée » ; l'alerte « Demande de prix »
du propriétaire est résolue (`PriceRequestExpired`, `sales/alerts.py`). **Idempotent** : un
second passage ne trouve plus rien et renvoie 0. Aucun acteur (action du serveur) : les règles
de vente lisent déjà le statut effectif, ce passage ne fait que l'inscrire.
"""

from datetime import datetime

from app.application.ports.uow import UnitOfWorkFactory
from app.application.sales.return_ports import PriceRequestRepository
from app.domain.shared.business_day import require_aware
from app.domain.shared.ids import ShopId


class ExpirePriceRequests:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    def execute(self, shop_id: ShopId, now: datetime) -> int:
        """Nombre de demandes passées « Expirée » dans la boutique."""
        instant = require_aware(now)
        expired = 0
        with self._uow_factory(shop_id) as uow:
            requests = PriceRequestRepository.within(uow)
            for request in requests.due_for_expiry(instant):
                if request.expire(instant):
                    requests.update(request)
                    expired += 1
            uow.commit()
        return expired
