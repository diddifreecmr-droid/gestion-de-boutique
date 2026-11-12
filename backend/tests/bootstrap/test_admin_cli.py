"""Commande de création de l'administrateur plateforme (premier démarrage en production, T25)."""

import getpass
import io

import pytest

from app.bootstrap.admin_cli import (
    AdminCreationRefused,
    create_platform_admin,
    main,
    read_password_interactively,
)
from app.bootstrap.config import Environment, Settings
from app.bootstrap.identity import IdentityModule, build_identity
from app.domain.identity.phone import PhoneNumber

STRONG = "Kribi-Garoua-2026"


@pytest.fixture
def identity() -> IdentityModule:
    return build_identity(Settings(ENVIRONMENT=Environment.TEST, _env_file=None))


def test_creates_an_admin_who_can_use_the_chosen_password(identity: IdentityModule) -> None:
    user_id = create_platform_admin(identity, phone="699 00 00 01", name="Admin", password=STRONG)
    with identity.uow_factory() as uow:
        user = uow.users.find_by_phone(PhoneNumber.parse("699000001"))
    assert user is not None
    assert user.id == user_id
    assert user.is_platform_admin
    assert not user.must_change_pin
    assert identity.hasher.verify(user.secret_hash, STRONG)


def test_refuses_a_weak_password(identity: IdentityModule) -> None:
    with pytest.raises(AdminCreationRefused, match="too_short"):
        create_platform_admin(identity, phone="699000001", name="Admin", password="court")


def test_refuses_a_phone_already_registered(identity: IdentityModule) -> None:
    create_platform_admin(identity, phone="699000001", name="Admin", password=STRONG)
    with pytest.raises(AdminCreationRefused, match="déjà inscrit"):
        create_platform_admin(identity, phone="699000001", name="Autre", password=STRONG)


def test_main_reports_success_and_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    argv = ["--phone", "699000001", "--name", "Admin"]
    assert main(argv, read_password=lambda: STRONG) == 0
    assert "Administrateur plateforme créé" in capsys.readouterr().out
    assert main(["--phone", "abc", "--name", "Admin"], read_password=lambda: STRONG) == 1
    assert "Numéro de téléphone invalide" in capsys.readouterr().err


def test_main_rejects_a_mismatched_confirmation(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")

    def mismatch() -> str:
        raise AdminCreationRefused("Les deux saisies diffèrent : aucun compte créé")

    assert main(["--phone", "699000001", "--name", "Admin"], read_password=mismatch) == 1
    assert "diffèrent" in capsys.readouterr().err


class _Tty(io.StringIO):
    def isatty(self) -> bool:
        return True


def test_password_is_read_from_a_pipe_or_typed_twice(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(f"{STRONG}\n"))
    assert read_password_interactively() == STRONG
    monkeypatch.setattr("sys.stdin", _Tty())
    typed = iter([STRONG, "autre-chose-0123"])
    monkeypatch.setattr(getpass, "getpass", lambda _prompt: next(typed))
    with pytest.raises(AdminCreationRefused, match="diffèrent"):
        read_password_interactively()
