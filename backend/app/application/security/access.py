"""Valeur d'une cellule de la matrice des droits (CDC § 4.2) et portées de requête (specs § 8.2).

Légende du CDC : « Tout » = voit et agit sur tout ; « Siens » = seulement ce qu'il a lui-même
créé ; « Lecture » = voit sans modifier ; « — » = n'apparaît pas à l'écran.
"""

from dataclasses import dataclass
from enum import StrEnum

from app.domain.shared.ids import UserId


class Access(StrEnum):
    """Accès accordé à un rôle pour une permission."""

    NONE = "none"
    """« — » : refusé (le serveur lève une erreur, RG-D01)."""

    OWN = "own"
    """« Siens », « Ses voyages », « Pour ses clients » : enregistrements de l'acteur seulement."""

    READ = "read"
    """« Lecture » : voit tout, sans modifier ; n'est valide que sur une permission de lecture."""

    ALL = "all"
    """« Tout » / « Oui » sans restriction de portée."""


@dataclass(frozen=True, slots=True)
class AllScope:
    """Aucun filtre supplémentaire : tous les enregistrements de la boutique."""


@dataclass(frozen=True, slots=True)
class OwnScope:
    """Filtre à ajouter **dans la requête** du dépôt : `<colonne d'attribution> = user_id`.

    La colonne dépend de l'agrégat et est choisie par le dépôt, par exemple `seller_id` (ventes),
    `responsible_seller_id` (créances, versements), `driver.user_id` (voyages), `created_by`
    (dépenses, déplacements).
    """

    user_id: UserId


type Scope = AllScope | OwnScope
