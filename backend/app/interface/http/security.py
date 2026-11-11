"""Dépendances d'authentification HTTP : appareil, identité, `Actor` (specs § 6.1, § 8.1).

- `X-Device-Id` (UUIDv7) est **obligatoire** sur ces routes : absent → 400, illisible → 400.
- `Authorization: Bearer <jeton>` absent ou mal formé → 401 `UNAUTHENTICATED`.
- `current_actor` reconstruit l'`Actor` à **chaque requête** : jeton + session relue (révocation
  immédiate) + rattachement relu pour la boutique `{shop_id}` du chemin (rôle jamais lu dans le
  jeton). Code provisoire non changé → 403 `PIN_CHANGE_REQUIRED`.

Usage dans un futur routeur de boutique :

    @router.get("/shops/{shop_id}/sales")
    def list_sales(actor: Annotated[Actor, Depends(guard.current_actor)]) -> ...
"""

from typing import Annotated

from fastapi import Depends, Header

from app.application.identity.use_cases.authenticate import Authenticate, AuthenticatedUser
from app.application.security.actor import Actor
from app.domain.identity.errors import Unauthenticated
from app.domain.shared.ids import DeviceId, ShopId

BEARER_PREFIX = "bearer "


def device_id(x_device_id: Annotated[str, Header(max_length=64)]) -> DeviceId:
    """En-tête `X-Device-Id` obligatoire, au format UUIDv7 (`InvalidIdentifier` sinon)."""
    return DeviceId.parse(x_device_id)


def bearer_token(authorization: Annotated[str | None, Header()] = None) -> str:
    if authorization is None or not authorization.lower().startswith(BEARER_PREFIX):
        msg = "Authentification requise"
        raise Unauthenticated(msg)
    token = authorization[len(BEARER_PREFIX) :].strip()
    if not token:
        msg = "Authentification requise"
        raise Unauthenticated(msg)
    return token


class AuthGuard:
    """Fournit les dépendances FastAPI `current_user` et `current_actor`."""

    def __init__(self, authenticate: Authenticate) -> None:
        self._authenticate = authenticate

    def current_user(
        self,
        token: Annotated[str, Depends(bearer_token)],
        device: Annotated[DeviceId, Depends(device_id)],
    ) -> AuthenticatedUser:
        """Identité vérifiée ; tolère le code provisoire (`/me`, `/auth/change-pin`)."""
        return self._authenticate.identify(token, device)

    def current_actor(
        self,
        shop_id: str,
        token: Annotated[str, Depends(bearer_token)],
        device: Annotated[DeviceId, Depends(device_id)],
    ) -> Actor:
        """Acteur d'une route `/shops/{shop_id}/…` : rattachement actif obligatoire."""
        identity = self._authenticate.identify(token, device)
        return self._authenticate.actor_for(identity, ShopId.parse(shop_id))
