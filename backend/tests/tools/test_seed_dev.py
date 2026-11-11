"""Script de démonstration `tools/seed_dev.py` (dev uniquement, idempotent, refusé en prod)."""

import pytest
from pydantic import SecretStr

from app.bootstrap.config import Environment, Settings
from app.infrastructure.system_clock import SystemClock
from tests.application.identity.support import FakeHasher
from tools import seed_dev
from tools.seed_dev import SeedRefused, main, seed


def test_seed_opens_motos_garoua_with_four_roles() -> None:
    settings = Settings(ENVIRONMENT=Environment.TEST, _env_file=None)
    report = seed(settings, hasher=FakeHasher())
    assert report.created
    assert report.shop_id is not None
    roles = [role for role, _, _ in report.accounts]
    assert roles == ["platform_admin", "owner", "seller", "accountant", "driver"]
    assert report.articles == 6
    assert report.movements == 9  # 2 + 2 + 2 + 1 + 2, NF125-2 en rupture


def test_seed_is_idempotent_on_a_shared_store(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(ENVIRONMENT=Environment.TEST, _env_file=None)
    from app.bootstrap import core

    shared = core.build_core(settings, SystemClock())
    monkeypatch.setattr(seed_dev, "build_core", lambda *_: shared)
    first = seed(settings, hasher=FakeHasher())
    again = seed(settings, hasher=FakeHasher())
    assert (again.created, again.shop_id) == (False, first.shop_id)


def test_seed_is_refused_in_prod() -> None:
    url = SecretStr("postgresql+psycopg://u:p@127.0.0.1:5432/boutique")
    settings = Settings(ENVIRONMENT=Environment.PROD, DATABASE_URL=url, _env_file=None)
    with pytest.raises(SeedRefused):
        seed(settings)


def test_main(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--x"]) == 2
    monkeypatch.setattr(
        seed_dev, "load_settings", lambda: Settings(ENVIRONMENT=Environment.TEST, _env_file=None)
    )
    monkeypatch.setattr(seed_dev, "seed", lambda s: seed(s, hasher=FakeHasher()))
    assert main([]) == 0
    assert "Motos Garoua" in capsys.readouterr().out
