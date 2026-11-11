"""Assemblage de l'identité (T08) : adaptateurs, cas d'utilisation, garde HTTP.

Persistance : seul l'adaptateur **mémoire** existe pour l'instant (l'adaptateur SQL de
`USER` / `DEVICE_SESSION` suivra T06). Avec `PERSISTENCE_BACKEND=postgres` :

- en `prod`, le démarrage est **refusé** (des comptes perdus à chaque redémarrage seraient une
  faille silencieuse) ;
- en `dev`, l'identité reste en mémoire et un avertissement est journalisé au démarrage.

Les rattachements viennent d'un `InMemoryMembershipDirectory` jusqu'à T10.
"""

import logging
from dataclasses import dataclass
from datetime import timedelta

from app.application.identity.ports import PasswordHasher
from app.application.identity.sessions import SessionIssuer, SessionPolicy
from app.application.identity.uow import IdentityUnitOfWorkFactory
from app.application.identity.use_cases.authenticate import Authenticate
from app.application.identity.use_cases.change_pin import ChangePin
from app.application.identity.use_cases.get_me import GetMe
from app.application.identity.use_cases.login import Login
from app.application.identity.use_cases.logout import Logout
from app.application.identity.use_cases.refresh_session import RefreshSession
from app.application.ports.clock import Clock
from app.bootstrap.config import Environment, PersistenceBackend, Settings
from app.infrastructure.auth.argon2_hasher import Argon2PasswordHasher
from app.infrastructure.auth.jwt_tokens import JwtTokenService
from app.infrastructure.auth.opaque_tokens import RandomRefreshSecrets
from app.infrastructure.persistence.memory.identity import MemoryIdentityUnitOfWorkFactory
from app.infrastructure.persistence.memory.memberships import InMemoryMembershipDirectory
from app.infrastructure.persistence.memory.platform_store import MemoryPlatformStore
from app.infrastructure.system_clock import SystemClock
from app.interface.http.routes.auth import AuthComponents
from app.interface.http.security import AuthGuard

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class IdentityModule:
    """Ce que la composition root (et les tests d'intégration) manipulent."""

    uow_factory: IdentityUnitOfWorkFactory
    memberships: InMemoryMembershipDirectory
    hasher: PasswordHasher
    clock: Clock
    auth: AuthComponents


def session_policy_from(settings: Settings) -> SessionPolicy:
    return SessionPolicy(
        access_ttl=timedelta(minutes=settings.ACCESS_TOKEN_TTL_MINUTES),
        refresh_ttl=timedelta(days=settings.REFRESH_TOKEN_TTL_DAYS),
        admin_session_ttl=timedelta(hours=settings.ADMIN_SESSION_TTL_HOURS),
    )


def _require_supported_backend(settings: Settings) -> None:
    if settings.persistence_backend is PersistenceBackend.MEMORY:
        return
    if settings.ENVIRONMENT is Environment.PROD:
        msg = "Identité : adaptateur SQL pas encore livré, démarrage refusé en prod"
        raise RuntimeError(msg)
    logger.warning("Identité en mémoire (adaptateur SQL à venir) : comptes perdus à l'arrêt")


def build_identity(
    settings: Settings,
    *,
    clock: Clock | None = None,
    hasher: PasswordHasher | None = None,
) -> IdentityModule:
    """`clock` et `hasher` sont injectables pour les tests (horloge figée, Argon2 allégé)."""
    _require_supported_backend(settings)
    clock = clock or SystemClock()
    hasher = hasher or Argon2PasswordHasher()
    uow_factory = MemoryIdentityUnitOfWorkFactory(MemoryPlatformStore())
    memberships = InMemoryMembershipDirectory()
    tokens = JwtTokenService(settings.JWT_SECRET.get_secret_value(), clock)
    secrets = RandomRefreshSecrets()
    issuer = SessionIssuer(tokens, secrets, session_policy_from(settings))
    authenticate = Authenticate(uow_factory, tokens, memberships, clock)
    auth = AuthComponents(
        login=Login(uow_factory, hasher, issuer, clock),
        refresh=RefreshSession(uow_factory, secrets, issuer, clock),
        logout=Logout(uow_factory, secrets, clock),
        change_pin=ChangePin(uow_factory, hasher, clock),
        get_me=GetMe(uow_factory, memberships),
        guard=AuthGuard(authenticate),
        clock=clock,
    )
    return IdentityModule(
        uow_factory=uow_factory, memberships=memberships, hasher=hasher, clock=clock, auth=auth
    )
