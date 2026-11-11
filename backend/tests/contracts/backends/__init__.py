"""Sélection de l'adaptateur sous contrat (`--backend=memory|postgres`).

Chaque adaptateur fournit un `ContractBackend` : une base vierge par test et des unités de
travail qui connaissent le port `WidgetRepository`. La suite de contrats ne dépend que de
cette interface : c'est ce qui prouve que la base est interchangeable (TR-02).
"""

from collections.abc import Sequence
from typing import Protocol

import pytest

from app.application.ports.event_handler import EventHandler
from app.application.ports.uow import UnitOfWork
from app.domain.shared.ids import ShopId
from tests.contracts.backends.memory import MemoryContractBackend

BACKENDS = ("memory", "postgres")
DEFAULT_BACKEND = "memory"
POSTGRES_PENDING = (
    "--backend=postgres : adaptateur PostgreSQL : T06 (pas encore livré). "
    "Seul --backend=memory est disponible en T05."
)


class ContractBackend(Protocol):
    def uow(self, shop_id: ShopId, handlers: Sequence[EventHandler] = ()) -> UnitOfWork:
        """Unité de travail neuve sur la base du test, avec ces handlers d'événements."""
        ...


def require_available(name: str) -> None:
    """Échec explicite (jamais de saut silencieux) pour un adaptateur non livré."""
    if name == "postgres":
        raise pytest.UsageError(POSTGRES_PENDING)
    if name not in BACKENDS:
        msg = f"Adaptateur inconnu : {name!r} (attendu : {', '.join(BACKENDS)})"
        raise pytest.UsageError(msg)


def build_backend(name: str) -> ContractBackend:
    require_available(name)
    return MemoryContractBackend()
