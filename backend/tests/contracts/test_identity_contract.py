"""Contrat des dépôts plateforme (identité, comptes commerçants) : mémoire, SQLite, PostgreSQL.

C'est la preuve exigée avant de démarrer l'identité sur PostgreSQL (T08 → T10).
"""

from datetime import timedelta

import pytest

from app.domain.identity.events import RevocationReason
from app.domain.identity.phone import PhoneNumber
from app.domain.identity.session import DeviceSession
from app.domain.identity.user import User
from app.domain.shared.errors import Duplicate, NotFound, VersionConflict
from app.domain.shared.ids import DeviceId, ShopId, UserId
from app.domain.shops.account import MerchantAccount
from tests.contracts.backends import ContractBackend
from tests.contracts.shop_data import NOW, commit_platform

PHONE = PhoneNumber.parse("677001122")


def new_user(phone: PhoneNumber = PHONE) -> User:
    return User.register(phone=phone, name="Awa", secret_hash="h$1")


def test_user_round_trip_with_both_lockouts(backend: ContractBackend) -> None:
    user = new_user()
    device = DeviceId.new()
    for _ in range(5):
        user.record_failed_attempt(NOW, device)
    user.record_failed_pin_change(NOW, device)
    user.events.pull()
    with backend.platform_uow() as uow:
        uow.users.add(user)
        uow.commit()
    with backend.platform_uow() as uow:
        read = uow.users.get(user.id)
        by_phone = uow.users.find_by_phone(PHONE)
        assert uow.users.find_by_phone(PhoneNumber.parse("677009999")) is None
    assert by_phone is not None
    assert by_phone.id == user.id
    assert (read.failed_attempts, read.locked_until, read.status) == (
        5,
        user.locked_until,
        user.status,
    )
    assert read.pin_change_lockout == user.pin_change_lockout
    assert (read.must_change_pin, read.version) == (True, 1)
    with backend.platform_uow() as uow, pytest.raises(NotFound):
        uow.users.get(UserId.new())


def test_phone_is_unique_and_versions_are_checked(backend: ContractBackend) -> None:
    user = new_user()
    with backend.platform_uow() as uow:
        uow.users.add(user)
        uow.commit()
    with pytest.raises(Duplicate) as caught:
        commit_platform(backend, lambda uow: uow.users.add(new_user()))
    assert caught.value.details["constraint"] == "user_phone"
    with backend.platform_uow() as reader:
        stale = reader.users.get(user.id)  # lu, puis modifié ailleurs (SQLite : pas d'imbrication)
    with backend.platform_uow() as second:
        theirs = second.users.get(user.id)
        theirs.rehash("h$2")
        second.users.update(theirs)
        second.commit()
    stale.rehash("h$3")
    with pytest.raises(VersionConflict):
        commit_platform(backend, lambda uow: uow.users.update(stale))


def test_sessions_by_user_and_device(backend: ContractBackend) -> None:
    user, device = new_user(), DeviceId.new()
    session = DeviceSession.open(
        user_id=user.id,
        device_id=device,
        device_label="Android",
        refresh_hash="r1",
        now=NOW,
        lifetime=timedelta(days=30),
        sliding=True,
    )
    with backend.platform_uow() as uow:
        uow.users.add(user)
        uow.sessions.add(session)
        uow.commit()
    with backend.platform_uow() as uow:
        assert uow.sessions.active_for_device(user.id, device) is not None
        stored = uow.sessions.get(session.id)
        stored.revoke(NOW, RevocationReason.LOGOUT)
        uow.sessions.update(stored)
        uow.commit()
    with backend.platform_uow() as uow:
        assert uow.sessions.active_for_device(user.id, device) is None
        [only] = uow.sessions.for_user(user.id)
        assert only.revoked
        assert only.revoked_at == NOW
        assert only.expires_at == session.expires_at


def test_merchant_account_round_trip(backend: ContractBackend) -> None:
    account = MerchantAccount.create(name="Moussa", phone=PHONE)
    shop = ShopId.new()
    account.register_shop(shop, "Motos Garoua")
    with backend.platform_uow() as uow:
        uow.merchants.add(account)
        uow.commit()
    with backend.platform_uow() as uow:
        read = uow.merchants.find_by_phone(PHONE)
        assert read is not None
        assert read.shop_names == {shop: "Motos Garoua"}
        assert uow.merchants.find_by_phone(PhoneNumber.parse("677009999")) is None
    rival = MerchantAccount.create(name="Autre", phone=PHONE)
    with pytest.raises(Duplicate) as caught:
        commit_platform(backend, lambda uow: uow.merchants.add(rival))
    assert caught.value.details["constraint"] == "merchant_account_phone"
