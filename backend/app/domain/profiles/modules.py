"""Modules de l'application (CDC § 3.1, décision client specs § 15.1 « Modules par boutique »).

- **Toujours actifs** (`MANDATORY_MODULES`) : socle, journal, catalogue et stock, ventes ; ils
  ne se désactivent jamais (`MODULE_MANDATORY`).
- **Facultatifs** (`OPTIONAL_MODULES`) : activés ou désactivés par l'administrateur plateforme
  seul, dans les limites du profil.
- **Dépendances** (`MODULE_REQUIRES`) : `transport` ⇒ `transfers` (un voyage déplace du stock) ;
  une combinaison qui les viole est refusée (`MODULE_DEPENDENCY`), à l'ouverture comme au réglage.
"""

from collections.abc import Iterable, Mapping
from enum import StrEnum
from types import MappingProxyType


class Module(StrEnum):
    CORE = "core"  # Socle : comptes, boutiques, utilisateurs, lieux, réglages, connexion
    CATALOG = "catalog"  # Catalogue et stock
    PURCHASES = "purchases"
    SALES = "sales"  # Ventes, clients et reçus
    RECEIVABLES = "receivables"  # Créances et versements
    EXPENSES = "expenses"
    TRANSFERS = "transfers"  # Transferts de stock
    TRANSPORT = "transport"  # Camions, chauffeurs, voyages (Motos seulement)
    DASHBOARD = "dashboard"
    IMPORT = "import"  # Import Excel
    AUDIT = "audit"  # Journal d'actions


MANDATORY_MODULES: frozenset[Module] = frozenset(
    {Module.CORE, Module.AUDIT, Module.CATALOG, Module.SALES}
)
"""Toujours actifs (décision client du 2026-11-12) : on ne les désactive jamais."""

ALL_MODULES: frozenset[Module] = frozenset(Module)
OPTIONAL_MODULES: frozenset[Module] = ALL_MODULES - MANDATORY_MODULES

MODULE_REQUIRES: Mapping[Module, frozenset[Module]] = MappingProxyType(
    {Module.TRANSPORT: frozenset({Module.TRANSFERS})}
)
"""Module → modules qu'il exige actifs avec lui."""


def missing_mandatory(modules: Iterable[Module]) -> list[Module]:
    """Modules obligatoires absents de `modules`, triés."""
    return sorted(MANDATORY_MODULES - frozenset(modules))


def broken_dependencies(modules: Iterable[Module]) -> list[tuple[Module, Module]]:
    """Couples `(module, module exigé absent)` de la combinaison, triés."""
    wanted = frozenset(modules)
    return sorted(
        (module, required)
        for module in wanted
        for required in MODULE_REQUIRES.get(module, frozenset())
        if required not in wanted
    )
