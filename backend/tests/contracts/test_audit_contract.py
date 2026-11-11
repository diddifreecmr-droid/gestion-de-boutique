"""Contrat du journal `AuditLog` : ajout seul, lecture filtrée et paginée, isolation (RG-J01)."""

from uuid import UUID

import pytest

from app.application.audit.ports import AuditLog, AuditQuery
from app.application.ports.errors import IsolationViolation
from app.application.ports.pagination import PageRequest
from app.domain.audit.values import AuditAction, EntityRef
from app.domain.shared.errors import Duplicate
from app.domain.shared.ids import ShopId, UserId
from tests.contracts.audited import append_all, entry, minutes
from tests.contracts.backends import ContractBackend
from tests.contracts.helpers import run_in_uow
from tests.contracts.widget import NOW


def search(
    backend: ContractBackend, shop: ShopId, query: AuditQuery | None = None, limit: int = 50
) -> list[UUID]:
    with backend.uow(shop) as uow:
        page = AuditLog.within(uow).search(query or AuditQuery(), PageRequest(limit))
    return [item.id.value for item in page.items]


def test_port_exposes_no_way_to_modify_or_delete() -> None:
    public = {name for name in dir(AuditLog) if not name.startswith("_")}
    assert public == {"append", "search", "within", "shop_id"}


def test_appended_entry_reads_back_identical(backend: ContractBackend, shop_a: ShopId) -> None:
    written = entry(shop_a)
    run_in_uow(backend, shop_a, lambda uow: append_all(uow, written))
    with backend.uow(shop_a) as uow:
        (read,) = AuditLog.within(uow).search(AuditQuery(), PageRequest()).items
    assert read == written
    assert read.changes[0].before == 780_000


def test_rollback_discards_the_entry(backend: ContractBackend, shop_a: ShopId) -> None:
    with backend.uow(shop_a) as uow:
        append_all(uow, entry(shop_a))
        uow.rollback()
    assert search(backend, shop_a) == []


def test_same_id_twice_is_a_duplicate(backend: ContractBackend, shop_a: ShopId) -> None:
    written = entry(shop_a)
    run_in_uow(backend, shop_a, lambda uow: append_all(uow, written))
    with pytest.raises(Duplicate):
        run_in_uow(backend, shop_a, lambda uow: append_all(uow, written))
    assert len(search(backend, shop_a)) == 1


def test_shop_b_never_reads_shop_a(
    backend: ContractBackend, shop_a: ShopId, shop_b: ShopId
) -> None:
    run_in_uow(backend, shop_a, lambda uow: append_all(uow, entry(shop_a)))
    assert search(backend, shop_b) == []
    with backend.uow(shop_b) as uow, pytest.raises(IsolationViolation):
        append_all(uow, entry(shop_a))


def test_most_recent_first_with_cursor_pagination(backend: ContractBackend, shop_a: ShopId) -> None:
    entries = [entry(shop_a, at=NOW + minutes(i)) for i in range(5)]
    run_in_uow(backend, shop_a, lambda uow: append_all(uow, *entries))
    expected = [e.id.value for e in reversed(entries)]
    seen: list[UUID] = []
    request = PageRequest(2)
    with backend.uow(shop_a) as uow:
        while True:
            page = AuditLog.within(uow).search(AuditQuery(), request)
            seen.extend(e.id.value for e in page.items)
            if page.next_cursor is None:
                break
            request = PageRequest(2, page.next_cursor)
    assert seen == expected


def test_filters_combine(backend: ContractBackend, shop_a: ShopId) -> None:
    paul, awa = UserId.new(), UserId.new()
    sale = EntityRef("sale", UserId.new().value, "V-000001")
    old = entry(shop_a, at=NOW - minutes(60 * 48), user=paul)
    login = entry(shop_a, user=awa, action=AuditAction.LOGIN, module="identity")
    history = entry(shop_a, user=paul, entity=sale, action=AuditAction.UPDATE)
    run_in_uow(backend, shop_a, lambda uow: append_all(uow, old, login, history))
    assert search(backend, shop_a, AuditQuery(user_id=paul)) == [history.id.value, old.id.value]
    assert search(backend, shop_a, AuditQuery(actions={AuditAction.LOGIN})) == [login.id.value]
    assert search(backend, shop_a, AuditQuery(modules={"identity"})) == [login.id.value]
    by_entity = AuditQuery(entity_type="sale", entity_id=sale.id)
    assert search(backend, shop_a, by_entity) == [history.id.value]
    recent = AuditQuery(since=NOW - minutes(60), until=NOW + minutes(1))
    assert set(search(backend, shop_a, recent)) == {login.id.value, history.id.value}
