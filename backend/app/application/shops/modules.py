"""Modules actifs d'une boutique, relus à chaque usage (décision client specs § 15.1).

- `ModuleGate.require(shop_id, module)` : garde **d'une route** de boutique, appelée par
  l'interface HTTP après le contrôle d'appartenance et avant tout traitement ; lit la boutique
  dans sa propre unité de travail (lecture seule).
- `require_module(uow, module)` / `module_enabled(uow, module)` : garde ou test **dans** la
  transaction d'un cas d'utilisation, pour l'effet d'un module sur un autre (vente à crédit
  sans `receivables`, dépense hors ligne sans `expenses`, alerte d'un module désactivé…).

Rien n'est mis en cache : un réglage de l'administrateur prend effet à la requête suivante.
Les données déjà saisies restent en base et réapparaissent à la réactivation.
"""

from app.application.ports.uow import UnitOfWork, UnitOfWorkFactory
from app.application.shops.ports import ShopRepository
from app.domain.profiles.modules import Module
from app.domain.shared.ids import ShopId


def module_enabled(uow: UnitOfWork, module: Module) -> bool:
    return ShopRepository.within(uow).current().has_module(module)


def require_module(uow: UnitOfWork, module: Module) -> None:
    """Lève `ModuleDisabled` (403 `MODULE_DISABLED`, `details.module`) si le module est éteint."""
    ShopRepository.within(uow).current().require_module(module)


def enabled_modules(uow: UnitOfWork) -> frozenset[Module]:
    return ShopRepository.within(uow).current().enabled_modules


class ModuleGate:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    def require(self, shop_id: ShopId, module: Module) -> None:
        with self._uow_factory(shop_id) as uow:
            require_module(uow, module)
