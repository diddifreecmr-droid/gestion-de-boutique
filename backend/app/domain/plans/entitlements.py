"""Droits d'offre : ce que l'offre d'une boutique lui ouvre (TR-26, D17, specs § 6.5).

Aujourd'hui une seule offre, **gratuite permanente** (CDC § 1.1), qui n'ouvre aucun droit
premium : `offline_capture` (saisie hors connexion) y est faux. L'administrateur plateforme
peut poser une surcharge par boutique (activer pour un essai, une recette) sans redéploiement.
"""

from collections.abc import Mapping
from enum import StrEnum
from types import MappingProxyType


class Entitlement(StrEnum):
    """Code stable d'un droit d'offre (stocké, renvoyé dans `error.details`)."""

    OFFLINE_CAPTURE = "offline_capture"
    """Saisie hors connexion et `POST /sync` (specs § 6.5) : fonction premium future."""


class PlanCode(StrEnum):
    FREE = "free"
    """Offre gratuite permanente (CDC § 1.1)."""


PLAN_ENTITLEMENTS: Mapping[PlanCode, frozenset[Entitlement]] = MappingProxyType(
    {PlanCode.FREE: frozenset()}
)
"""Droits ouverts par chaque offre ; une offre absente de la table est une erreur."""


def plan_grants(plan: PlanCode, entitlement: Entitlement) -> bool:
    """Vrai si l'offre `plan` comprend `entitlement` ; `KeyError` pour une offre inconnue."""
    if not isinstance(entitlement, Entitlement):
        msg = f"Droit d'offre inconnu : {entitlement!r}"
        raise TypeError(msg)
    return entitlement in PLAN_ENTITLEMENTS[plan]
