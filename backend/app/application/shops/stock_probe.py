"""Port `LocationStock` : un lieu a-t-il du stock ? (UC-SOC-05 « un lieu qui a du stock ne peut
pas être désactivé », recette LOC-02).

Le stock n'existe qu'avec le module Stock (T14), qui implémentera ce port sur sa projection
`stock_level`, dans la transaction de l'unité de travail reçue.

**PROVISOIRE (T10 → T14)** : `NoStockRecorded` répond toujours « aucun stock », ce qui est
exact tant qu'aucun mouvement de stock ne peut être enregistré. La composition root le
remplacera par l'adaptateur de T14 ; il ne doit pas lui survivre.
"""

from abc import ABC, abstractmethod

from app.application.ports.uow import UnitOfWork
from app.domain.shops.ids import LocationId


class LocationStock(ABC):
    @abstractmethod
    def has_stock(self, uow: UnitOfWork, location_id: LocationId) -> bool:
        """Vrai si une quantité non nulle (vendable, abîmée ou en route) est au lieu."""


class NoStockRecorded(LocationStock):
    """PROVISOIRE jusqu'à T14 : aucun mouvement de stock n'existe encore."""

    def has_stock(self, uow: UnitOfWork, location_id: LocationId) -> bool:
        return False
