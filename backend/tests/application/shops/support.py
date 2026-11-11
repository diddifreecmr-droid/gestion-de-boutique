"""Monde de test du socle : noyau mémoire réel (`build_core`), horloge figée, hachage factice.

`World.open_motos()` ouvre « Motos Garoua » comme l'administrateur ; `member(...)` ajoute un
membre et renvoie son `Actor`.
"""

from collections.abc import Iterator
from dataclasses import dataclass, field

from app.application.audit.ports import AuditLog, AuditQuery
from app.application.identity.ports import TemporaryPinGenerator
from app.application.ports.pagination import PageRequest
from app.application.security.actor import Actor
from app.application.shops.ports import LocationRepository
from app.application.shops.use_cases.manage_members import AddedMember, AddMemberCommand
from app.application.shops.use_cases.open_shop import OpenedShop, OpenShopCommand
from app.bootstrap.config import Environment, Settings
from app.bootstrap.core import Core, build_core
from app.bootstrap.identity import IdentityModule, build_identity
from app.bootstrap.shops import ShopsModule, build_shops
from app.domain.audit.entry import AuditEntry
from app.domain.identity.phone import PhoneNumber
from app.domain.identity.user import User
from app.domain.shared.ids import DeviceId, ShopId, UserId
from app.domain.shared.roles import Role
from app.domain.shops.ids import LocationId
from app.domain.shops.location import Location
from app.infrastructure.persistence.memory.clock import FixedClock
from tests.application.identity.support import PASSWORD, T0, FakeHasher

ADMIN_PHONE = "600000001"
OWNER_PHONE = "690000001"


class FixedPins(TemporaryPinGenerator):
    """Codes provisoires prévisibles (non simples) pour les assertions."""

    def __init__(self) -> None:
        self.codes: Iterator[str] = iter(f"{n:06d}" for n in range(482915, 999999, 7919))

    def generate(self) -> str:
        return next(self.codes)


def motos_command(name: str = "Motos Garoua", owner_phone: str = OWNER_PHONE) -> OpenShopCommand:
    return OpenShopCommand(
        profile_code="motos",
        name=name,
        city="Garoua",
        phone="222000000",
        owner_name="Moussa",
        owner_phone=owner_phone,
    )


@dataclass
class World:
    clock: FixedClock = field(default_factory=lambda: FixedClock(T0))
    hasher: FakeHasher = field(default_factory=FakeHasher)

    def __post_init__(self) -> None:
        settings = Settings(ENVIRONMENT=Environment.TEST, _env_file=None)
        self.core: Core = build_core(settings, self.clock)
        self.identity: IdentityModule = build_identity(settings, hasher=self.hasher, core=self.core)
        self.pins = FixedPins()
        self.shops: ShopsModule = build_shops(self.identity, pins=self.pins)
        self.http = self.shops.http
        admin = User.register(
            phone=PhoneNumber.parse(ADMIN_PHONE),
            name="Admin",
            secret_hash=self.hasher.hash(PASSWORD),
            is_platform_admin=True,
            must_change_pin=False,
        )
        self.save_user(admin)
        self.admin = Actor.platform_admin(user_id=admin.id, device_id=DeviceId.new())

    def save_user(self, user: User) -> None:
        with self.core.platform_uow_factory() as uow:
            uow.users.add(user)
            uow.commit()

    def user(self, phone: str) -> User:
        with self.core.platform_uow_factory() as uow:
            found = uow.users.find_by_phone(PhoneNumber.parse(phone))
        assert found is not None
        return found

    def open_motos(self, name: str = "Motos Garoua", owner_phone: str = OWNER_PHONE) -> OpenedShop:
        return self.http.open_shop.execute(self.admin, motos_command(name, owner_phone))

    def owner(self, opened: OpenedShop) -> Actor:
        return self.actor(opened.shop_id, opened.owner_id, Role.OWNER)

    @staticmethod
    def shop_of(actor: Actor) -> ShopId:
        assert actor.shop_id is not None
        return actor.shop_id

    @staticmethod
    def actor(shop_id: ShopId, user_id: UserId, role: Role) -> Actor:
        return Actor.member(user_id=user_id, device_id=DeviceId.new(), shop_id=shop_id, role=role)

    def location(self, shop_id: ShopId, name: str) -> Location:
        with self.core.shop_uow_factory(shop_id) as uow:
            return next(
                loc for loc in LocationRepository.within(uow).list_all() if loc.name == name
            )

    def location_id(self, shop_id: ShopId, name: str) -> LocationId:
        return self.location(shop_id, name).id

    def add(
        self, owner: Actor, phone: str, role: Role, location: str | None = None, name: str = "Paul"
    ) -> AddedMember:
        assert owner.shop_id is not None
        location_id = None if location is None else self.location_id(owner.shop_id, location)
        command = AddMemberCommand(
            name=name, phone=phone, role=role, default_location_id=location_id
        )
        return self.http.members.add(owner, command)

    def member(self, owner: Actor, phone: str, role: Role, location: str | None = None) -> Actor:
        added = self.add(owner, phone, role, location)
        assert owner.shop_id is not None
        return self.actor(owner.shop_id, added.member.membership.user_id, role)

    def journal(self, shop_id: ShopId, query: AuditQuery | None = None) -> list[AuditEntry]:
        with self.core.shop_uow_factory(shop_id) as uow:
            page = AuditLog.within(uow).search(query or AuditQuery(), PageRequest(limit=200))
        return list(page.items)
