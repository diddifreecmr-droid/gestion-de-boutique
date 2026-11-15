"""Orchestration du jeu de démonstration : trois boutiques, une par type, idempotent.

Une boutique dont le **nom** existe déjà (catalogue plateforme) est laissée telle quelle : la
relance ne crée rien en double. Une boutique est créée d'un bloc par les cas d'utilisation ;
une erreur arrête tout (fail-fast) — la boutique partiellement remplie reste alors visible et
sera ignorée à la relance (la supprimer, ou la renommer, avant de relancer).
"""

from dataclasses import dataclass, field

from app.application.security.actor import Actor
from app.bootstrap.identity import IdentityModule
from app.bootstrap.seed_demo.activity import run_activity
from app.bootstrap.seed_demo.apparel import APPAREL_PLAN
from app.bootstrap.seed_demo.motos import MOTOS_PLAN
from app.bootstrap.seed_demo.opening import open_demo_shop
from app.bootstrap.seed_demo.plan import ShopPlan
from app.bootstrap.seed_demo.services import build_services
from app.bootstrap.seed_demo.textile import TEXTILE_PLAN
from app.domain.identity.phone import PhoneNumber
from app.domain.shared.ids import DeviceId

PLANS: tuple[ShopPlan, ...] = (MOTOS_PLAN, APPAREL_PLAN, TEXTILE_PLAN)
ALREADY_THERE = "(boutique déjà présente)"


class DemoSeedRefused(RuntimeError):
    """Démonstration impossible (administrateur introuvable ou sans droit plateforme)."""


@dataclass(frozen=True, slots=True)
class AccountRow:
    shop: str
    role: str
    name: str
    phone: str
    code: str


@dataclass
class DemoReport:
    rows: list[AccountRow] = field(default_factory=list)
    created: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    sales: int = 0


def platform_admin(identity: IdentityModule, phone: str) -> Actor:
    """L'administrateur plateforme existant qui « ouvre » les boutiques (journal d'actions)."""
    with identity.uow_factory() as uow:
        user = uow.users.find_by_phone(PhoneNumber.parse(phone))
    if user is None or not user.is_platform_admin:
        msg = f"Aucun administrateur plateforme au numéro {phone} (créez-le : admin_cli)"
        raise DemoSeedRefused(msg)
    return Actor.platform_admin(user_id=user.id, device_id=DeviceId.new())


def seed_demo(
    identity: IdentityModule, admin_phone: str, *, skip: frozenset[str] = frozenset()
) -> DemoReport:
    """`skip` : noms à considérer comme déjà présents (simulation `--dry-run`)."""
    services = build_services(identity)
    admin = platform_admin(identity, admin_phone)
    existing = {summary.name for summary in identity.core.catalog.list_all()} | skip
    report = DemoReport()
    for plan in PLANS:
        if plan.name in existing:
            report.skipped.append(plan.name)
            report.rows += [
                AccountRow(plan.name, p.label, p.name, p.phone, ALREADY_THERE) for p in plan.people
            ]
            continue
        services.clock.at(10)
        opened = open_demo_shop(services, admin, plan)
        report.sales += run_activity(services, plan, opened)
        report.created.append(plan.name)
        report.rows += [
            AccountRow(plan.name, p.label, p.name, p.phone, opened.codes[p.phone])
            for p in plan.people
        ]
    services.clock.reset()
    return report
