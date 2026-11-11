"""Monde de test de l'identité : horloge figée, mémoire, JWT réel, hachage factice rapide."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.application.identity.ports import IdentityEventHandler, PasswordHasher
from app.application.identity.sessions import IssuedSession, SessionIssuer, SessionPolicy
from app.application.identity.uow import IdentityUnitOfWork
from app.application.identity.use_cases.authenticate import Authenticate, AuthenticatedUser
from app.application.identity.use_cases.login import CredentialKind, Login, LoginCommand
from app.application.identity.use_cases.member_access import MemberAccess
from app.application.security.policy import Policy
from app.application.security.roles import Role
from app.domain.identity.events import IdentityEvent
from app.domain.identity.phone import PhoneNumber
from app.domain.identity.user import User
from app.domain.shared.ids import DeviceId, ShopId
from app.infrastructure.auth.jwt_tokens import JwtTokenService
from app.infrastructure.auth.opaque_tokens import RandomRefreshSecrets
from app.infrastructure.persistence.memory.clock import FixedClock
from app.infrastructure.persistence.memory.identity import MemoryIdentityUnitOfWorkFactory
from app.infrastructure.persistence.memory.memberships import InMemoryMembershipDirectory
from app.infrastructure.persistence.memory.platform_store import MemoryPlatformStore

T0 = datetime(2026, 11, 11, 8, 0, tzinfo=UTC)
SECRET = "secret-de-test-assez-long-pour-hs256-0123456789"
PIN = "482915"
PASSWORD = "Garoua-Boulai-2026!"
SHOP = ShopId.new()
OTHER_SHOP = ShopId.new()


class FakeHasher(PasswordHasher):
    """`fake$<version>$<secret>` : instantané ; la version `v0` « demande un rehachage »."""

    def __init__(self, version: str = "v1") -> None:
        self.version = version

    def hash(self, secret: str) -> str:
        return f"fake${self.version}${secret}"

    def verify(self, secret_hash: str, secret: str) -> bool:
        prefix, _, rest = secret_hash.partition("$")
        if prefix != "fake":
            msg = "empreinte illisible"
            raise ValueError(msg)
        return rest.partition("$")[2] == secret

    def needs_rehash(self, secret_hash: str) -> bool:
        return not secret_hash.startswith(f"fake${self.version}$")


class RecordingHandler(IdentityEventHandler):
    def __init__(self) -> None:
        self.received: list[IdentityEvent] = []

    def handle(self, event: IdentityEvent, uow: IdentityUnitOfWork) -> None:
        self.received.append(event)


@dataclass
class World:
    clock: FixedClock = field(default_factory=lambda: FixedClock(T0))
    hasher: FakeHasher = field(default_factory=FakeHasher)
    store: MemoryPlatformStore = field(default_factory=MemoryPlatformStore)
    memberships: InMemoryMembershipDirectory = field(default_factory=InMemoryMembershipDirectory)
    policy_settings: SessionPolicy = field(default_factory=SessionPolicy)
    recorder: RecordingHandler = field(default_factory=RecordingHandler)

    def __post_init__(self) -> None:
        self.uow_factory = MemoryIdentityUnitOfWorkFactory(self.store, [self.recorder])
        self.tokens = JwtTokenService(SECRET, self.clock)
        self.secrets = RandomRefreshSecrets()
        self.issuer = SessionIssuer(self.tokens, self.secrets, self.policy_settings)
        self.login_uc = Login(
            self.uow_factory, self.hasher, self.issuer, self.clock, self.memberships
        )
        self.authenticate = Authenticate(
            self.uow_factory, self.tokens, self.memberships, self.clock
        )
        self.policy = Policy(clock=self.clock.now)
        self.access = MemberAccess(self.policy, self.memberships)

    def register(
        self,
        phone: str = "677 00 11 22",
        secret: str = PIN,
        *,
        admin: bool = False,
        must_change: bool = False,
        role: Role | None = Role.SELLER,
        shop: ShopId = SHOP,
    ) -> User:
        user = User.register(
            phone=PhoneNumber.parse(phone),
            name="Awa Bello",
            secret_hash=self.hasher.hash(secret),
            is_platform_admin=admin,
            must_change_pin=must_change,
        )
        with self.uow_factory() as uow:
            uow.users.add(user)
            uow.commit()
        if role is not None and not admin:
            self.memberships.grant(user.id, shop, "Motos Garoua", role)
        return user

    def login(
        self,
        phone: str = "677001122",
        secret: str = PIN,
        *,
        device: DeviceId | None = None,
        kind: CredentialKind = CredentialKind.PIN,
    ) -> IssuedSession:
        command = LoginCommand(
            phone=phone,
            secret=secret,
            kind=kind,
            device_id=device or DeviceId.new(),
            device_label="Android — Chrome",
        )
        return self.login_uc.execute(command)

    def user(self, user: User) -> User:
        with self.uow_factory() as uow:
            return uow.users.get(user.id)

    def save(self, user: User) -> None:
        with self.uow_factory() as uow:
            uow.users.update(user)
            uow.commit()

    def identity(self, issued: IssuedSession, device: DeviceId) -> AuthenticatedUser:
        return self.authenticate.identify(issued.access_token, device)
