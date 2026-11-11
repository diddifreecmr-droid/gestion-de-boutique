"""Assemblage de l'identité (T08, T10) : adaptateurs, cas d'utilisation, garde HTTP.

Persistance : celle du noyau (`core.py`) — mémoire, ou PostgreSQL (`app_user`,
`device_session`, migration 0003) ; l'identité démarre donc aussi en prod. Les rattachements
sont lus sur l'agrégat `Membership`, les délégations de l'administrateur sur
`ADMIN_ACCESS_GRANT` (chaque accès délégué est journalisé). Limitation de débit de `/auth/*` :
voir `throttle_from` (désactivée en `ENVIRONMENT=test` sauf `AUTH_RATE_LIMIT_ENABLED=true`).
"""

from dataclasses import dataclass
from datetime import timedelta

from app.application.identity.ports import MembershipDirectory, PasswordHasher
from app.application.identity.sessions import SessionIssuer, SessionPolicy
from app.application.identity.uow import IdentityUnitOfWorkFactory
from app.application.identity.use_cases.authenticate import Authenticate, Delegations
from app.application.identity.use_cases.change_pin import ChangePin
from app.application.identity.use_cases.get_me import GetMe
from app.application.identity.use_cases.login import Login
from app.application.identity.use_cases.logout import Logout
from app.application.identity.use_cases.refresh_session import RefreshSession
from app.application.ports.clock import Clock
from app.application.security.rate_limit import AuthThrottle, RateLimitRule
from app.application.shops.delegated_access import AuditDelegatedAccess
from app.bootstrap.config import Environment, Settings
from app.bootstrap.core import Core, build_core
from app.infrastructure.auth.argon2_hasher import Argon2PasswordHasher
from app.infrastructure.auth.jwt_tokens import JwtTokenService
from app.infrastructure.auth.opaque_tokens import RandomRefreshSecrets
from app.infrastructure.rate_limit import InMemoryRateLimiter
from app.infrastructure.system_clock import SystemClock
from app.interface.http.routes.auth import AuthComponents
from app.interface.http.security import AuthGuard


@dataclass(frozen=True, slots=True, kw_only=True)
class IdentityModule:
    """Ce que la composition root (et les tests d'intégration) manipulent."""

    uow_factory: IdentityUnitOfWorkFactory
    memberships: MembershipDirectory
    hasher: PasswordHasher
    clock: Clock
    auth: AuthComponents
    core: Core


def session_policy_from(settings: Settings) -> SessionPolicy:
    return SessionPolicy(
        access_ttl=timedelta(minutes=settings.ACCESS_TOKEN_TTL_MINUTES),
        refresh_ttl=timedelta(days=settings.REFRESH_TOKEN_TTL_DAYS),
        admin_session_ttl=timedelta(hours=settings.ADMIN_SESSION_TTL_HOURS),
    )


def throttle_from(settings: Settings, clock: Clock) -> AuthThrottle | None:
    """Limitation de débit (specs § 8.1) ; `None` = désactivée (tests par défaut)."""
    enabled = settings.AUTH_RATE_LIMIT_ENABLED
    if enabled is None:
        enabled = settings.ENVIRONMENT is not Environment.TEST
    if not enabled:
        return None
    return AuthThrottle(
        InMemoryRateLimiter(),
        clock,
        per_ip=RateLimitRule("auth_ip", settings.AUTH_RATE_LIMIT_PER_IP, timedelta(minutes=1)),
        per_phone=RateLimitRule(
            "auth_phone", settings.AUTH_RATE_LIMIT_PER_PHONE, timedelta(minutes=15)
        ),
    )


def build_identity(
    settings: Settings,
    *,
    clock: Clock | None = None,
    hasher: PasswordHasher | None = None,
    core: Core | None = None,
) -> IdentityModule:
    """`clock`, `hasher` et `core` sont injectables (tests : horloge figée, Argon2 allégé)."""
    if core is None:
        core = build_core(settings, clock or SystemClock())
    elif clock is not None and clock is not core.clock:
        msg = "build_identity : l'horloge fournie diffère de celle du noyau"
        raise ValueError(msg)
    clock, hasher = core.clock, hasher or Argon2PasswordHasher()
    uow_factory, memberships = core.platform_uow_factory, core.memberships
    tokens = JwtTokenService(settings.JWT_SECRET.get_secret_value(), clock)
    secrets = RandomRefreshSecrets()
    issuer = SessionIssuer(tokens, secrets, session_policy_from(settings))
    delegations = Delegations(
        directory=core.delegations, journal=AuditDelegatedAccess(core.shop_uow_factory, clock)
    )
    authenticate = Authenticate(uow_factory, tokens, memberships, clock, delegations)
    auth = AuthComponents(
        login=Login(uow_factory, hasher, issuer, clock, memberships),
        refresh=RefreshSession(uow_factory, secrets, issuer, clock, memberships),
        logout=Logout(uow_factory, secrets, clock),
        change_pin=ChangePin(uow_factory, hasher, clock),
        get_me=GetMe(uow_factory, memberships),
        guard=AuthGuard(authenticate),
        clock=clock,
        throttle=throttle_from(settings, clock),
    )
    return IdentityModule(
        uow_factory=uow_factory,
        memberships=memberships,
        hasher=hasher,
        clock=clock,
        auth=auth,
        core=core,
    )
