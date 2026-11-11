"""Établir l'identité d'une requête puis l'`Actor` d'une boutique (specs § 8.1, § 8.3).

`identify` (toute route authentifiée) : jeton d'accès valide → session relue **à chaque
requête** (révocation immédiate, recette SEC-R02 / Q-42), appareil identique à celui de la
session, compte non désactivé (SEC-X02). Le code provisoire est toléré ici : `/me` et
`/auth/change-pin` doivent répondre (AUTH-02).

`actor_for` (routes de boutique) : code provisoire → `PinChangeRequired` ; rôle relu dans le
rattachement **actif** de la boutique (jamais dans le jeton) ; sans rattachement →
`NotFound`, comme une boutique inexistante (aucune fuite). L'administrateur plateforme reçoit
un `Actor` sans rôle et sans délégation : `ADMIN_ACCESS_GRANT` arrive avec T10/T11, la
`Policy` le traite donc comme un non-membre (404).
"""

from dataclasses import dataclass

from app.application.identity.ports import MembershipDirectory, TokenService
from app.application.identity.uow import IdentityUnitOfWorkFactory
from app.application.ports.clock import Clock
from app.application.security.actor import Actor
from app.domain.identity.errors import PinChangeRequired, SessionRevoked, Unauthenticated
from app.domain.identity.events import SessionId
from app.domain.shared.errors import NotFound
from app.domain.shared.ids import DeviceId, ShopId, UserId

SHOP_NOT_FOUND_MESSAGE = "Boutique introuvable"


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthenticatedUser:
    """Identité vérifiée d'une requête (avant choix de la boutique)."""

    user_id: UserId
    session_id: SessionId
    device_id: DeviceId
    is_platform_admin: bool
    must_change_pin: bool


class Authenticate:
    def __init__(
        self,
        uow_factory: IdentityUnitOfWorkFactory,
        tokens: TokenService,
        memberships: MembershipDirectory,
        clock: Clock,
    ) -> None:
        self._uow_factory = uow_factory
        self._tokens = tokens
        self._memberships = memberships
        self._clock = clock

    def identify(self, access_token: str, device_id: DeviceId) -> AuthenticatedUser:
        claims = self._tokens.verify(access_token)
        now = self._clock.now()
        with self._uow_factory() as uow:
            session = uow.sessions.find(claims.session_id)
            if session is None or session.user_id != claims.user_id:
                raise SessionRevoked
            if session.device_id != device_id:
                msg = "Jeton émis pour un autre appareil"
                raise Unauthenticated(msg)
            if not session.is_active(now):
                raise SessionRevoked
            user = uow.users.get(claims.user_id)
            user.ensure_active()
        return AuthenticatedUser(
            user_id=user.id,
            session_id=session.id,
            device_id=device_id,
            is_platform_admin=user.is_platform_admin,
            must_change_pin=user.must_change_pin,
        )

    def actor_for(self, identity: AuthenticatedUser, shop_id: ShopId) -> Actor:
        if identity.must_change_pin:
            raise PinChangeRequired
        if identity.is_platform_admin:
            return Actor.platform_admin(
                user_id=identity.user_id, device_id=identity.device_id, shop_id=shop_id
            )
        membership = self._memberships.find(identity.user_id, shop_id)
        if membership is None or not membership.active:
            raise NotFound(SHOP_NOT_FOUND_MESSAGE)
        return Actor.member(
            user_id=identity.user_id,
            device_id=identity.device_id,
            shop_id=shop_id,
            role=membership.role,
        )
