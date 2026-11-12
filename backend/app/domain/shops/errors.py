"""Erreurs métier du socle (codes **ajoutés** par T10, recette Q-31) → HTTP 422 sauf mention.

| Erreur | Code | Cas |
| --- | --- | --- |
| `LastActiveOwner` | `LAST_ACTIVE_OWNER` | RG-D08 : retirer le dernier propriétaire actif |
| `LastPointOfSale` | `LAST_POINT_OF_SALE` | retirer le dernier point de vente actif (CDC § 20.1) |
| `LocationHasStock` | `LOCATION_HAS_STOCK` | UC-SOC-05 : lieu qui a du stock (LOC-02) |
| `LocationInUse` | `LOCATION_IN_USE` | lieu habituel d'un vendeur, lieu de réception |
| `NotPointOfSale` | `LOCATION_NOT_POINT_OF_SALE` | lieu habituel hors point de vente (MEM-01) |
| `RoleNotOffered` | `ROLE_NOT_IN_PROFILE` | rôle absent du profil (Chauffeur hors Motos) |
| `ModuleNotAvailable` | `MODULE_NOT_AVAILABLE` | module absent du profil de la boutique |
| `ModuleMandatory` | `MODULE_MANDATORY` | désactiver un module toujours actif (§ 15.1) |
| `ModuleDependency` | `MODULE_DEPENDENCY` | `transport` sans `transfers` (§ 15.1) |
| `ModuleDisabled` | `MODULE_DISABLED` | **403** : fonction d'un module désactivé de la boutique |
| `UnknownProfile` | `UNKNOWN_PROFILE` | 400 : code de profil inconnu |
"""

from app.domain.shared.errors import DomainError, Forbidden, ValidationFailed


class LastActiveOwner(DomainError):
    code = "LAST_ACTIVE_OWNER"

    def __init__(self) -> None:
        super().__init__("Une boutique garde toujours au moins un propriétaire actif")


class LastPointOfSale(DomainError):
    code = "LAST_POINT_OF_SALE"

    def __init__(self) -> None:
        super().__init__("Une boutique garde toujours au moins un point de vente actif")


class LocationHasStock(DomainError):
    code = "LOCATION_HAS_STOCK"

    def __init__(self, location: str) -> None:
        super().__init__(
            "Ce lieu a du stock : déplacez ou ajustez son stock d'abord",
            details={"location_id": location},
        )


class LocationInUse(DomainError):
    code = "LOCATION_IN_USE"

    def __init__(self, location: str, usage: str) -> None:
        super().__init__(
            "Ce lieu est encore utilisé", details={"location_id": location, "usage": usage}
        )


class NotPointOfSale(DomainError):
    code = "LOCATION_NOT_POINT_OF_SALE"

    def __init__(self, location: str) -> None:
        super().__init__(
            "Le lieu de vente habituel doit être un point de vente actif",
            details={"location_id": location},
        )


class RoleNotOffered(DomainError):
    code = "ROLE_NOT_IN_PROFILE"

    def __init__(self, role: str, profile: str) -> None:
        super().__init__(
            "Ce rôle n'existe pas pour ce type de boutique",
            details={"role": role, "profile": profile},
        )


class ModuleNotAvailable(DomainError):
    code = "MODULE_NOT_AVAILABLE"

    def __init__(self, module: str, profile: str) -> None:
        super().__init__(
            "Module indisponible pour ce type de boutique",
            details={"module": module, "profile": profile},
        )


class ModuleMandatory(DomainError):
    code = "MODULE_MANDATORY"

    def __init__(self, module: str) -> None:
        super().__init__(
            "Ce module est toujours actif : il ne se désactive pas", details={"module": module}
        )


class ModuleDependency(DomainError):
    code = "MODULE_DEPENDENCY"

    def __init__(self, module: str, requires: str) -> None:
        super().__init__(
            "Ce module exige un autre module actif",
            details={"module": module, "requires": requires},
        )


class ModuleDisabled(Forbidden):
    """403 : la boutique n'a pas ce module (ses routes, ou l'effet d'un autre module : vente à
    crédit sans `receivables`…). Contrôlé après l'appartenance : un non-membre garde 404."""

    code = "MODULE_DISABLED"

    def __init__(self, module: str) -> None:
        super().__init__(
            "Cette fonction n'est pas activée pour la boutique", details={"module": module}
        )


class UnknownProfile(ValidationFailed):
    code = "UNKNOWN_PROFILE"

    def __init__(self, code: str) -> None:
        super().__init__(
            "Type de boutique inconnu", details={"field": "profile_code", "value": code[:32]}
        )
