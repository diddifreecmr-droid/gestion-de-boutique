"""Données de démonstration (**dev uniquement**) : la boutique « Motos Garoua » et ses comptes.

Ouvre la boutique (profil Motos) par le vrai cas d'utilisation `OpenShop`, comme
l'administrateur, puis ajoute un vendeur (Garoua), un comptable et un chauffeur par
`ManageMembers`. Les codes sont fixés (connus, non simples) pour les essais du frontend : ils
ne servent **jamais** ailleurs qu'en démonstration. Relancer ne recrée rien (idempotent).

Refusé si `ENVIRONMENT=prod` (`SeedRefused`) ; `tools/` n'est pas copié dans l'image de
production (T25). Usage (depuis `backend/`, base migrée) :

    uv run python -m tools.seed_dev
"""

import sys
from collections.abc import Sequence
from dataclasses import dataclass, field

from app.application.identity.ports import PasswordHasher
from app.application.security.actor import Actor
from app.application.shops.ports import LocationRepository
from app.application.shops.use_cases.manage_members import AddMemberCommand
from app.application.shops.use_cases.open_shop import OpenShopCommand
from app.bootstrap.config import Environment, Settings, load_settings
from app.bootstrap.core import build_core
from app.bootstrap.identity import IdentityModule, build_identity
from app.bootstrap.shops import build_shops
from app.domain.identity.phone import PhoneNumber
from app.domain.identity.user import User
from app.domain.shared.ids import DeviceId, ShopId
from app.domain.shared.roles import Role
from app.infrastructure.system_clock import SystemClock

SHOP_NAME = "Motos Garoua"
ADMIN = ("699000000", "Admin démo", "Demo-Admin-2026!")
OWNER = ("690000001", "Moussa (propriétaire)", "482915")
MEMBERS = (
    ("690000002", "Paul (vendeur)", "593026", Role.SELLER),
    ("690000003", "Aïcha (comptable)", "604137", Role.ACCOUNTANT),
    ("690000004", "Bello (chauffeur)", "715248", Role.DRIVER),
)


class SeedRefused(RuntimeError):
    """Démonstration demandée hors développement."""


@dataclass
class SeedReport:
    shop_id: ShopId | None = None
    created: bool = False
    accounts: list[tuple[str, str, str]] = field(default_factory=list)
    """(rôle, téléphone, code ou mot de passe)."""


def _set_secret(identity: IdentityModule, phone: str, secret: str) -> None:
    """Code connu et définitif (démonstration) : `must_change_pin` levé."""
    with identity.uow_factory() as uow:
        user = uow.users.find_by_phone(PhoneNumber.parse(phone))
        if user is None:
            msg = f"Compte de démonstration introuvable : {phone}"
            raise RuntimeError(msg)
        user.rehash(identity.hasher.hash(secret))
        user.must_change_pin = False
        uow.users.update(user)
        uow.commit()


def _admin(identity: IdentityModule) -> Actor:
    phone, name, password = ADMIN
    with identity.uow_factory() as uow:
        admin = uow.users.find_by_phone(PhoneNumber.parse(phone))
        if admin is None:
            admin = User.register(
                phone=PhoneNumber.parse(phone),
                name=name,
                secret_hash=identity.hasher.hash(password),
                is_platform_admin=True,
                must_change_pin=False,
            )
            uow.users.add(admin)
            uow.commit()
    return Actor.platform_admin(user_id=admin.id, device_id=DeviceId.new())


def seed(settings: Settings, hasher: PasswordHasher | None = None) -> SeedReport:
    if settings.ENVIRONMENT is Environment.PROD:
        msg = "Données de démonstration refusées en prod"
        raise SeedRefused(msg)
    core = build_core(settings, SystemClock())
    identity = build_identity(settings, hasher=hasher, core=core)
    shops = build_shops(identity).http
    admin = _admin(identity)
    report = SeedReport(accounts=[("platform_admin", ADMIN[0], ADMIN[2])])
    existing = [s for s in core.catalog.list_all() if s.name == SHOP_NAME]
    if existing:
        report.shop_id = existing[0].shop_id
        return report
    command = OpenShopCommand(
        profile_code="motos",
        name=SHOP_NAME,
        city="Garoua",
        phone="222270000",
        owner_name=OWNER[1],
        owner_phone=OWNER[0],
    )
    opened = shops.open_shop.execute(admin, command)
    owner = Actor.member(
        user_id=opened.owner_id, device_id=DeviceId.new(), shop_id=opened.shop_id, role=Role.OWNER
    )
    with core.shop_uow_factory(opened.shop_id) as uow:
        garoua = next(
            loc for loc in LocationRepository.within(uow).list_all() if loc.name == "Garoua"
        )
    for phone, name, _, role in MEMBERS:
        location = garoua.id if role is Role.SELLER else None
        shops.members.add(
            owner, AddMemberCommand(name=name, phone=phone, role=role, default_location_id=location)
        )
    for phone, _, secret, *rest in (OWNER, *MEMBERS):
        _set_secret(identity, phone, secret)
        report.accounts.append((rest[0].value if rest else Role.OWNER.value, phone, secret))
    report.shop_id, report.created = opened.shop_id, True
    return report


def main(argv: Sequence[str] | None = None) -> int:
    if argv:
        print("Usage : python -m tools.seed_dev (aucun argument)", file=sys.stderr)
        return 2
    report = seed(load_settings())
    state = "créée" if report.created else "déjà présente"
    print(f"Boutique « {SHOP_NAME} » {state} : {report.shop_id}")
    for role, phone, secret in report.accounts:
        print(f"  {role:<15} {phone}  {secret}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
