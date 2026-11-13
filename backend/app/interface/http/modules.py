"""Module de chaque route de boutique (décision client specs § 15.1 « Modules par boutique »).

Chaque routeur de boutique est monté par `ShopRoutes.include(routeur, module, overrides)` :

- chaque route reçoit la dépendance `AuthGuard.module_dependency(module)` : appartenance
  d'abord (non-membre → 404), puis module (éteint → 403 `MODULE_DISABLED`), puis la route ;
- l'OpenAPI déclare le module de l'opération dans l'extension `x-module` (contrat lisible par
  le frontend et par le garde-fou de recette) ;
- `overrides` : préfixe de chemin (après `/shops/{shop_id}`) → module, pour un routeur qui
  mêle deux modules (journal et alertes, tableau de bord et accueil).

Exception unique : une route **à lien signé** (`SIGNED_LINK`, contenu d'une pièce jointe) n'a
ni jeton ni acteur ; elle déclare son module sans garde, car le lien n'est délivré que par une
route gardée (`GET /attachments/{id}/url`, module de l'élément lié vérifié) et expire en 60 s.

`require_declared_modules` refuse au démarrage une route de boutique sans module (fail-fast).
"""

from collections.abc import Mapping

from fastapi import APIRouter, Depends, FastAPI
from fastapi.routing import APIRoute

from app.domain.profiles.modules import Module
from app.interface.http.security import AuthGuard

SHOP_PATH = "/shops/{shop_id}"
MODULE_EXTENSION = "x-module"
SIGNED_LINK_EXTENSION = "x-signed-link"
SIGNED_LINK = {SIGNED_LINK_EXTENSION: True}
"""`openapi_extra` d'une route sans jeton, ouverte par un lien signé (voir l'en-tête)."""


def _module_of(suffix: str, default: Module, overrides: Mapping[str, Module]) -> Module:
    for path, module in overrides.items():
        if suffix == path or suffix.startswith(f"{path}/"):
            return module
    return default


class ShopRoutes:
    def __init__(self, app: FastAPI, guard: AuthGuard, prefix: str) -> None:
        self._app = app
        self._guard = guard
        self._prefix = prefix

    def include(
        self,
        router: APIRouter,
        module: Module,
        overrides: Mapping[str, Module] | None = None,
    ) -> None:
        for route in router.routes:
            if not isinstance(route, APIRoute) or not route.path.startswith(f"{SHOP_PATH}/"):
                msg = f"Route hors boutique dans un routeur de boutique : {route!r}"
                raise ValueError(msg)
            declared = _module_of(route.path.removeprefix(SHOP_PATH), module, overrides or {})
            if not (route.openapi_extra or {}).get(SIGNED_LINK_EXTENSION):
                route.dependencies.append(Depends(self._guard.module_dependency(declared)))
            route.openapi_extra = {**(route.openapi_extra or {}), MODULE_EXTENSION: declared.value}
        self._app.include_router(router, prefix=self._prefix)


def route_module(route: APIRoute) -> Module | None:
    declared = (route.openapi_extra or {}).get(MODULE_EXTENSION)
    return None if declared is None else Module(declared)


def require_declared_modules(app: FastAPI, prefix: str) -> None:
    """Toute route `/shops/{shop_id}/…` montée déclare son module ; sinon `RuntimeError`."""
    missing = [
        f"{sorted(route.methods or ())} {route.path}"
        for route in app.routes
        if isinstance(route, APIRoute)
        and route.path.startswith(f"{prefix}{SHOP_PATH}/")
        and route_module(route) is None
    ]
    if missing:
        msg = f"Routes de boutique sans module déclaré : {missing}"
        raise RuntimeError(msg)
