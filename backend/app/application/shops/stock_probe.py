"""Port `LocationStock` : un lieu a-t-il du stock ? (UC-SOC-05 « un lieu qui a du stock ne peut
pas être désactivé », recette LOC-02).

Implémenté par le module Stock (T14) sur sa projection `stock_level`, dans la transaction de
l'unité de travail reçue : `application/stock/probes.py` (`LedgerLocationStock`), branché par
`bootstrap/shops.py`. L'implémentation provisoire de T10 a été retirée.
"""

from abc import ABC, abstractmethod

from app.application.ports.uow import UnitOfWork
from app.domain.shops.ids import LocationId


class LocationStock(ABC):
    @abstractmethod
    def has_stock(self, uow: UnitOfWork, location_id: LocationId) -> bool:
        """Vrai si une quantité non nulle (vendable, abîmée ou en route) est au lieu."""
