"""Validation d'une combinaison de modules de boutique (décision client specs § 15.1).

Ordre des contrôles, premier refus seulement (message stable, testable) :

1. module hors du profil → `MODULE_NOT_AVAILABLE` (si `available` est donné) ;
2. module obligatoire absent → `MODULE_MANDATORY` (on ne désactive jamais un obligatoire) ;
3. dépendance non tenue (`transport` sans `transfers`) → `MODULE_DEPENDENCY`.

Toutes ces erreurs sont des règles métier → HTTP 422.
"""

from collections.abc import Iterable

from app.domain.profiles.modules import Module, broken_dependencies, missing_mandatory
from app.domain.profiles.profile import ProfileCode
from app.domain.shops.errors import ModuleDependency, ModuleMandatory, ModuleNotAvailable


def checked_modules(
    modules: Iterable[Module],
    *,
    profile: ProfileCode,
    available: frozenset[Module] | None = None,
) -> frozenset[Module]:
    """La combinaison `modules` validée (voir l'en-tête du module)."""
    wanted = frozenset(Module(m) for m in modules)
    unavailable = [] if available is None else sorted(wanted - available)
    if unavailable:
        raise ModuleNotAvailable(unavailable[0].value, ProfileCode(profile).value)
    missing = missing_mandatory(wanted)
    if missing:
        raise ModuleMandatory(missing[0].value)
    broken = broken_dependencies(wanted)
    if broken:
        module, required = broken[0]
        raise ModuleDependency(module.value, required.value)
    return wanted
