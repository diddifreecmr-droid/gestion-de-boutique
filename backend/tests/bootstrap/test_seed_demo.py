"""Jeu de démonstration `python -m app.bootstrap.seed_demo` sur le backend mémoire."""

from datetime import timedelta

import pytest

from app.application.sales.ports import SaleRepository
from app.application.stock.reading import all_articles
from app.bootstrap.admin_cli import create_platform_admin
from app.bootstrap.config import Settings
from app.bootstrap.core import build_core
from app.bootstrap.identity import IdentityModule, build_identity
from app.bootstrap.seed_demo.__main__ import main
from app.bootstrap.seed_demo.seed import ALREADY_THERE, DemoSeedRefused, seed_demo
from app.bootstrap.seed_demo.services import ReplayClock
from app.domain.identity.phone import PhoneNumber
from app.domain.sales.values import SaleKind
from app.infrastructure.system_clock import SystemClock
from tests.application.identity.support import FakeHasher

ADMIN = "699000000"
SHOPS = ["Démo Motos", "Démo Prêt-à-porter", "Démo Tissus"]


@pytest.fixture
def identity(settings: Settings) -> IdentityModule:
    core = build_core(settings, ReplayClock(SystemClock().now()))
    module = build_identity(settings, hasher=FakeHasher(), core=core)
    create_platform_admin(module, phone=ADMIN, name="Admin", password="Admin-demo-2026!")
    return module


def test_seed_creates_three_shops_with_staff_and_history(identity: IdentityModule) -> None:
    report = seed_demo(identity, ADMIN)
    assert report.created == SHOPS
    assert report.sales == 36
    assert len(report.rows) == 12
    assert len({row.phone for row in report.rows}) == 12
    assert all(row.phone.startswith("690001") for row in report.rows)
    with identity.uow_factory() as uow:
        user = uow.users.find_by_phone(PhoneNumber.parse(report.rows[1].phone))
    assert user is not None
    assert user.must_change_pin
    assert user.secret_hash == f"fake$v1${report.rows[1].code}"
    start = identity.clock.now()
    shops = {s.name: s.shop_id for s in identity.core.catalog.list_all()}
    with identity.core.shop_uow_factory(shops["Démo Tissus"]) as uow:
        articles = all_articles(uow)
        today = identity.clock.today()
        sales = SaleRepository.within(uow).list_between(today - timedelta(days=7), today)
    assert len({a.details.fields.fabric for a in articles}) == 10
    assert len(sales) == 12
    assert len({s.seller_id for s in sales}) == 2
    assert [s.kind for s in sales].count(SaleKind.CREDIT) == 1
    assert all(start - timedelta(days=7) < s.sold_at <= start for s in sales)


def test_seed_is_idempotent(identity: IdentityModule) -> None:
    seed_demo(identity, ADMIN)
    again = seed_demo(identity, ADMIN)
    assert (again.created, again.skipped, again.sales) == ([], SHOPS, 0)
    assert {row.code for row in again.rows} == {ALREADY_THERE}
    names = [s.name for s in identity.core.catalog.list_all()]
    assert sorted(names) == sorted(SHOPS)


def test_seed_requires_an_existing_platform_admin(identity: IdentityModule) -> None:
    with pytest.raises(DemoSeedRefused):
        seed_demo(identity, "699999999")


def test_main_dry_run_and_failure(settings: Settings, capsys: pytest.CaptureFixture[str]) -> None:
    args = ["--admin-phone", ADMIN, "--dry-run"]
    assert main(args, settings=settings, hasher=FakeHasher()) == 0
    out = capsys.readouterr().out
    assert "rien n'a été écrit" in out
    assert "Démo Tissus" in out
    assert "Code provisoire" in out
    assert main(["--admin-phone", ADMIN], settings=settings, hasher=FakeHasher()) == 1
