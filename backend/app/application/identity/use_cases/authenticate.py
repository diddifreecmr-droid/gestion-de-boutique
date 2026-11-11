"""Établir l'identité d'une requête puis l'`Actor` d'une boutique (specs § 8.1, § 8.3).

`identify` (toute route authentifiée) : jeton d'accès valide → session relue **à chaque
requête** (révocation immédiate, recette SEC-R02 / Q-42), appareil identique à celui de la
session, compte non désactivé et doté d'au moins un rattachement utilisable (SEC-X02, RG-D06
par boutique). Le code provisoire est toléré ici : `/me` et `/auth/change-pin` doivent
répondre (AUTH-02).

`actor_for` (routes de boutique) : code provisoire → `PinChangeRequired` ; rôle relu dans le
rattachement de la boutique (jamais dans le jeton). Sans rattachement, ou boutique fermée →
`NotFound`, comme une boutique inexistante (aucune fuite) ; rattachement **désactivé** →
`AccountDisabled` (403, « Compte désactivé, contactez le propriétaire »). L'administrateur
plateforme reçoit un `Actor` sans rôle, avec la délégation active de la boutique s'il y en a
une (`ADMIN_ACCESS_GRANT`, T10) : sans elle, la `Policy` le traite comme un non-membre (404) ;
avec elle, chacun de ses accès est inscrit au journal de la boutique (specs § 8.3).

`platform_actor` (console `/platform/*`) : réservé à l'administrateur ; un membre reçoit 403.
"""

import logging
from dataclasses import dataclass

from app.application.identity.ports import (
    AdminDelegationDirectory,
    DelegatedAccessJournal,
    MembershipDirectory,
    TokenService,
)
from app.application.identity.reachability import require_reachable
from app.application.identity.uow import IdentityUnitOfWorkFactory
from app.application.ports.clock import Clock
from app.application.security.actor import Actor, AdminDelegation
from app.domain.identity.errors import (
    AccountDisabled,
    PinChangeRequired,
    SessionRevoked,
    Unauthenticated,
)
from app.domain.identity.events import SessionId
from app.domain.shared.errors import Forbidden, NotFound
from app.domain.shared.ids import DeviceId, ShopId, UserId

SHOP_NOT_FOUND_MESSAGE = "Boutique introuvable"
platform_log = logging.getLogger("app.audit.platform")


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthenticatedUser:
    """Identité vérifiée d'une requête (avant choix de la boutique)."""

    user_id: UserId
    session_id: SessionId
    device_id: DeviceId
    is_platform_admin: bool
    must_change_pin: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class Delegations:
    """Lecture des délégations et journal des accès : toujours fournis ensemble."""

    directory: AdminDelegationDirectory
    journal: DelegatedAccessJournal


class Authenticate:
    def __init__(
        self,
        uow_factory: IdentityUnitOfWorkFactory,
        tokens: TokenService,
        memberships: MembershipDirectory,
        clock: Clock,
        delegations: Delegations | None = None,
    ) -> None:
        """`delegations=None` : aucune délégation n'existe (l'admin est toujours un tiers)."""
        self._uow_factory = uow_factory
        self._tokens = tokens
        self._memberships = memberships
        self._clock = clock
        self._delegations = delegations

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
        require_reachable(self._memberships, user)
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
            return self._admin_actor(identity, shop_id)
        membership = self._memberships.find(identity.user_id, shop_id)
        if membership is None or not membership.shop_active:
            raise NotFound(SHOP_NOT_FOUND_MESSAGE)
        if not membership.active:
            raise AccountDisabled
        return Actor.member(
            user_id=identity.user_id,
            device_id=identity.device_id,
            shop_id=shop_id,
            role=membership.role,
        )

    def platform_actor(self, identity: AuthenticatedUser) -> Actor:
        """Acteur de la console plateforme ; `Forbidden` (journal plateforme) pour un membre."""
        if identity.must_change_pin:
            raise PinChangeRequired
        if not identity.is_platform_admin:
            platform_log.warning(
                "Console plateforme refusée user=%s device=%s",
                identity.user_id,
                identity.device_id,
            )
            msg = "Accès refusé"
            raise Forbidden(msg, details={"permission": "PLATFORM_ADMIN"})
        return Actor.platform_admin(user_id=identity.user_id, device_id=identity.device_id)

    def _admin_actor(self, identity: AuthenticatedUser, shop_id: ShopId) -> Actor:
        delegation = None
        if self._delegations is not None:
            until = self._delegations.directory.active_until(shop_id, self._clock.now())
            if until is not None:
                delegation = AdminDelegation(shop_id, until)
        actor = Actor.platform_admin(
            user_id=identity.user_id,
            device_id=identity.device_id,
            shop_id=shop_id,
            delegation=delegation,
        )
        if delegation is not None and self._delegations is not None:
            self._delegations.journal.record(actor)
        return actor
