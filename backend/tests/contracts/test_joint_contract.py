"""Contrat de la transaction commune plateforme + boutique (T10) et des lectures plateforme.

- tout est validé ensemble, ou rien : une erreur au commit, une unité jointe qui échoue ou une
  unité plateforme annulée n'écrivent ni le compte ni la boutique ;
- les handlers de boutique (journal) écrivent dans la même transaction ;
- `MembershipDirectory`, `ShopCatalog`, `AdminDelegationDirectory` lisent l'état validé.
"""

from datetime import timedelta

import pytest

from app.application.audit.identity_recorder import IdentityAuditRecorder
from app.application.audit.ports import AuditLog, AuditQuery
from app.application.audit.recorder import AuditRecorder
from app.application.identity.uow import IdentityUnitOfWork
from app.application.ports.errors import UnitOfWorkStateError
from app.application.ports.pagination import PageRequest
from app.application.shops.ports import AdminGrantRepository, MembershipRepository, ShopRepository
from app.domain.audit.values import Performer
from app.domain.identity.phone import PhoneNumber
from app.domain.identity.user import User
from app.domain.shared.errors import Duplicate
from app.domain.shared.ids import DeviceId, ShopId
from app.domain.shared.roles import Role
from app.domain.shops.account import MerchantAccount
from app.domain.shops.admin_grant import AdminAccessGrant
from app.domain.shops.ids import MerchantAccountId
from app.domain.shops.membership import Membership
from app.infrastructure.persistence.memory.clock import FixedClock
from tests.contracts.backends import ContractBackend
from tests.contracts.shop_data import NOW, shop

PHONE = PhoneNumber.parse("690000001")


def owner_membership(shop_id: ShopId, user: User) -> Membership:
    performer = Performer(user.id, "platform_admin")
    from app.domain.profiles.motos import MOTOS

    return Membership.add(
        shop_id=shop_id, user_id=user.id, role=Role.OWNER, location=None, profile=MOTOS,
        performer=performer, now=NOW,
    )  # fmt: skip


def open_jointly(backend: ContractBackend, shop_id: ShopId) -> tuple[User, MerchantAccount]:
    user = User.register(phone=PHONE, name="Moussa", secret_hash="h")
    account = MerchantAccount.create(name="Moussa", phone=PHONE)
    account.register_shop(shop_id, "Motos Garoua")
    with backend.platform_uow(shop_handlers=[AuditRecorder(FixedClock(NOW))]) as uow:
        uow.users.add(user)
        uow.merchants.add(account)
        with uow.join_shop(shop_id) as shop_uow:
            ShopRepository.within(shop_uow).add(shop(shop_id, account.id))
            MembershipRepository.within(shop_uow).add(owner_membership(shop_id, user))
            shop_uow.commit()
        uow.commit()
    return user, account


def journal(backend: ContractBackend, shop_id: ShopId) -> list[str]:
    with backend.uow(shop_id) as uow:
        page = AuditLog.within(uow).search(AuditQuery(), PageRequest(limit=50))
    return [entry.summary for entry in page.items]


def test_joint_commit_writes_both_sides_and_the_journal(
    backend: ContractBackend, shop_a: ShopId
) -> None:
    user, account = open_jointly(backend, shop_a)
    [view] = backend.memberships().for_user(user.id)
    assert (view.shop_id, view.shop_name, view.role, view.usable) == (
        shop_a,
        "Motos Garoua",
        Role.OWNER,
        True,
    )
    assert backend.memberships().find(user.id, ShopId.new()) is None
    [summary] = backend.catalog().list_all()
    assert (summary.account_id, summary.account_name) == (account.id, "Moussa")
    assert backend.catalog().find(ShopId.new()) is None
    assert journal(backend, shop_a) == ["Utilisateur ajouté (owner)"]


def test_a_commit_conflict_leaves_nothing(backend: ContractBackend, shop_a: ShopId) -> None:
    open_jointly(backend, shop_a)
    other = ShopId.new()
    with pytest.raises(Duplicate):
        open_jointly(backend, other)  # même téléphone : compte et utilisateur en double
    assert backend.catalog().find(other) is None
    assert journal(backend, other) == []


def failing_join(uow: IdentityUnitOfWork, shop_id: ShopId) -> None:
    with uow.join_shop(shop_id) as shop_uow:
        ShopRepository.within(shop_uow).add(shop(shop_id, MerchantAccountId.new()))
        msg = "panne après une écriture jointe"
        raise RuntimeError(msg)


def test_failed_joined_unit_dooms_the_transaction(backend: ContractBackend, shop_a: ShopId) -> None:
    user = User.register(phone=PHONE, name="Moussa", secret_hash="h")
    with backend.platform_uow() as uow:
        uow.users.add(user)
        with pytest.raises(RuntimeError, match="panne"):
            failing_join(uow, shop_a)
        with pytest.raises(UnitOfWorkStateError):
            uow.commit()
    with backend.platform_uow() as uow:
        assert uow.users.find_by_phone(PHONE) is None
    assert backend.catalog().find(shop_a) is None


def test_read_only_joined_unit_does_not_doom(backend: ContractBackend, shop_a: ShopId) -> None:
    user = User.register(phone=PHONE, name="Moussa", secret_hash="h")
    with backend.platform_uow() as uow:
        uow.users.add(user)
        with uow.join_shop(shop_a) as shop_uow:
            assert MembershipRepository.within(shop_uow).list_all() == []
        uow.commit()
    with backend.platform_uow() as uow:
        assert uow.users.find_by_phone(PHONE) is not None


def test_identity_events_reach_the_shop_journal_in_the_same_transaction(
    backend: ContractBackend, shop_a: ShopId
) -> None:
    user, _ = open_jointly(backend, shop_a)
    recorder = IdentityAuditRecorder(backend.memberships(), FixedClock(NOW))
    with backend.platform_uow(handlers=[recorder]) as uow:
        stored = uow.users.get(user.id)
        stored.record_failed_attempt(NOW, DeviceId.new())
        uow.users.update(stored)
        uow.commit()
    assert "Échec de connexion" in journal(backend, shop_a)


def test_delegations_directory(backend: ContractBackend, shop_a: ShopId) -> None:
    assert backend.delegations().active_until(shop_a, NOW) is None
    grant = AdminAccessGrant.grant(
        shop_id=shop_a,
        performer=Performer(User.register(phone=PHONE, name="O", secret_hash="h").id, "owner"),
        now=NOW,
    )
    with backend.uow(shop_a) as uow:
        AdminGrantRepository.within(uow).add(grant)
        uow.commit()
    assert backend.delegations().active_until(shop_a, NOW) == grant.expires_at
    assert backend.delegations().active_until(shop_a, NOW + timedelta(days=2)) is None
    assert backend.delegations().active_until(ShopId.new(), NOW) is None
