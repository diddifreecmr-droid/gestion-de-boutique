"""Port `EventHandler` : traitement des événements de domaine **dans la transaction** (D7, TR-09).

Un handler (journal, alertes…) reçoit chaque événement à valider et l'unité de travail en
cours : il écrit par ses dépôts, dans la même transaction. S'il lève une exception, toute la
transaction est annulée et l'exception remonte à l'appelant (jamais avalée).
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from app.domain.shared.events import DomainEvent

if TYPE_CHECKING:
    from app.application.ports.uow import UnitOfWork


class EventHandler(ABC):
    """Reçoit tous les événements ; ignore ceux qui ne le concernent pas."""

    @abstractmethod
    def handle(self, event: DomainEvent, uow: "UnitOfWork") -> None:
        """Traite `event` ; toute exception annule la transaction entière."""
