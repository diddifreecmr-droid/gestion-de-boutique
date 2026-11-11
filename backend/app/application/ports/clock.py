"""Port `Clock` : seule source de l'heure courante pour l'application (TR-07).

Aucun cas d'utilisation ne lit `datetime.now()` : l'horloge est injectée, ce qui rend les
règles de date (RG-T09) testables avec une horloge figée.
"""

from abc import ABC, abstractmethod
from datetime import date, datetime

from app.domain.shared.business_day import business_date


class Clock(ABC):
    """Horloge de l'application."""

    @abstractmethod
    def now(self) -> datetime:
        """Instant courant, **aware et en UTC** (un instant naïf est une erreur d'adaptateur)."""

    def today(self) -> date:
        """Date métier courante (heure du Cameroun), dérivée de `now()`."""
        return business_date(self.now())
