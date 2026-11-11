"""Sélection de l'adaptateur sous contrat (`--backend=memory|postgres`).

Chaque adaptateur fournit un `ContractBackend` : une base vierge par test et des unités de
travail qui connaissent le port `WidgetRepository`. La suite de contrats ne dépend que de
cette interface : c'est ce qui prouve que la base est interchangeable (TR-02).
"""

from collections.abc import Sequence
from typing import Protocol

import pytest

from app.application.plans.ports import EntitlementOverrides
from app.application.ports.event_handler import EventHandler
from app.application.ports.uow import UnitOfWork
from app.domain.shared.ids import ShopId
from tests.contracts.backends import postgres
from tests.contracts.backends.memory import MemoryContractBackend

BACKENDS = ("memory", "postgres")
DEFAULT_BACKEND = "memory"


class ContractBackend(Protocol):
    def uow(self, shop_id: ShopId, handlers: Sequence[EventHandler] = ()) -> UnitOfWork:
        """Unité de travail neuve sur la base du test, avec ces handlers d'événements."""
        ...

    def entitlement_overrides(self) -> EntitlementOverrides:
        """Surcharges de droits d'offre sur la base du test (portée plateforme)."""
        ...


def require_available(name: str) -> None:
    """Prépare l'adaptateur ; échec explicite (jamais de saut silencieux) s'il est injoignable."""
    if name not in BACKENDS:
        msg = f"Adaptateur inconnu : {name!r} (attendu : {', '.join(BACKENDS)})"
        raise pytest.UsageError(msg)
    if name == "postgres":
        postgres.prepare()


def build_backend(name: str) -> ContractBackend:
    """Base vierge pour un test."""
    if name == "postgres":
        return postgres.PostgresContractBackend()
    require_available(name)
    return MemoryContractBackend()


def release() -> None:
    """Fin de session : rend les connexions ouvertes par `prepare`."""
    postgres.dispose()
