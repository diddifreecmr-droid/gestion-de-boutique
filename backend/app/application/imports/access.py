"""Droits sur un modèle d'import (matrice specs § 4.2, recette Lot 3 M3-01 à M3-04).

Ordre : modèle connu (404) → modules exigés par le modèle (403 `MODULE_DISABLED`, IMP-11) →
permission du modèle (403 `FORBIDDEN`, journalisé). Le module `import` lui-même est contrôlé
plus tôt, par la garde de la route (specs § 15.1).
"""

from app.application.imports.models import ImportModel, ImportModels
from app.application.ports.uow import UnitOfWork
from app.application.security.actor import Actor
from app.application.security.policy import Policy
from app.application.shops.modules import require_module
from app.application.shops.ports import ShopRepository
from app.domain.profiles.profile import ShopProfile
from app.domain.profiles.registry import profile_for


class ImportAccess:
    def __init__(self, policy: Policy, models: ImportModels) -> None:
        self._policy = policy
        self._models = models

    def require(self, uow: UnitOfWork, actor: Actor, kind: str) -> ImportModel:
        model = self._models.get(kind)
        for module in sorted(model.modules):
            require_module(uow, module)
        self._policy.require(actor, model.permission)
        return model


def shop_profile(uow: UnitOfWork) -> ShopProfile:
    return profile_for(ShopRepository.within(uow).current().profile_code)
