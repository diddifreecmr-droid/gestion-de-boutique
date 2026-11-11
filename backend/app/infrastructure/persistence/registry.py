"""Choix de l'adaptateur servant un port de dépôt, commun à toutes les unités de travail.

Les dépôts disponibles sont déclarés par la liste de leurs **classes d'adaptateur** (fournie par
la composition root ou par les tests) : l'unité de travail ne grossit pas à chaque module. Le
port demandé est servi par l'unique adaptateur qui en hérite.
"""

from collections.abc import Sequence
from typing import Any

from app.application.ports.repository import Repository


def select_adapter[AdapterT: type[Repository[Any, Any]]](
    registry: Sequence[AdapterT], port: type[Repository[Any, Any]], kind: str
) -> AdapterT:
    """Unique adaptateur de `registry` qui implémente `port` ; `LookupError` sinon."""
    candidates = [adapter for adapter in registry if issubclass(adapter, port)]
    if len(candidates) != 1:
        found = ", ".join(adapter.__name__ for adapter in candidates) or "aucun"
        msg = f"Il faut un et un seul adaptateur {kind} pour {port.__name__} ({found})"
        raise LookupError(msg)
    return candidates[0]
