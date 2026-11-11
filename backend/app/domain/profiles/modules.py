"""Modules de l'application (CDC § 3.1) : le socle plus dix modules, code stable."""

from enum import StrEnum


class Module(StrEnum):
    CORE = "core"  # Socle : comptes, boutiques, utilisateurs, lieux, réglages, connexion
    CATALOG = "catalog"  # Catalogue et stock
    PURCHASES = "purchases"
    SALES = "sales"  # Ventes et reçus
    RECEIVABLES = "receivables"  # Créances et versements
    EXPENSES = "expenses"
    TRANSFERS = "transfers"  # Transferts de stock
    TRANSPORT = "transport"  # Camions, chauffeurs, voyages (Motos seulement)
    DASHBOARD = "dashboard"
    IMPORT = "import"  # Import Excel
    AUDIT = "audit"  # Journal d'actions


MANDATORY_MODULES: frozenset[Module] = frozenset({Module.CORE, Module.AUDIT})
"""Toujours actifs : sans socle rien ne marche, sans journal aucune trace (RG-T01)."""

ALL_MODULES: frozenset[Module] = frozenset(Module)
