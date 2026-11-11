"""Mémoire : revalidation au commit contre les transactions concurrentes (entrelacées).

Ces scénarios entrelacent deux transactions ouvertes qui écrivent les mêmes données. Ils ne
sont pas dans le contrat commun : sur PostgreSQL, la seconde écriture **attendrait** le verrou
de ligne de la première, ce qu'un test monothread ne peut pas exprimer (voir T06).
"""

import pytest

from app.domain.shared.doc_number import DocType
from app.domain.shared.errors import Duplicate, VersionConflict
from app.domain.shared.ids import ShopId
from tests.contracts.backends.memory import MemoryContractBackend
from tests.contracts.helpers import committed_widget, read_widget, widgets
from tests.contracts.widget import Widget


@pytest.fixture
def backend() -> MemoryContractBackend:
    return MemoryContractBackend()


@pytest.fixture
def shop() -> ShopId:
    return ShopId.new()


def test_concurrent_number_allocation_fails_the_second_commit(
    backend: MemoryContractBackend, shop: ShopId
) -> None:
    with backend.uow(shop) as first, backend.uow(shop) as second:
        assert str(first.numbering.next(DocType.SALE)) == "V-000001"
        assert str(second.numbering.next(DocType.SALE)) == "V-000001"
        first.commit()
        with pytest.raises(VersionConflict):
            second.commit()
    with backend.uow(shop) as uow:
        assert str(uow.numbering.next(DocType.SALE)) == "V-000002"  # aucun doublon, aucun trou
        uow.commit()


def test_concurrent_updates_fail_the_second_commit(
    backend: MemoryContractBackend, shop: ShopId
) -> None:
    widget = committed_widget(backend, shop, "v1")
    with backend.uow(shop) as first, backend.uow(shop) as second:
        mine, theirs = widgets(first).get(widget.id), widgets(second).get(widget.id)
        mine.label, theirs.label = "premier", "second"
        widgets(first).update(mine)
        widgets(second).update(theirs)
        first.commit()
        with pytest.raises(VersionConflict):
            second.commit()
    assert read_widget(backend, shop, widget).label == "premier"


def test_concurrent_inserts_of_the_same_code_fail_the_second_commit(
    backend: MemoryContractBackend, shop: ShopId
) -> None:
    loser = Widget.create(shop, "b", code="CH-1")
    with backend.uow(shop) as first, backend.uow(shop) as second:
        widgets(first).add(Widget.create(shop, "a", code="CH-1"))
        widgets(second).add(loser)
        first.commit()
        with pytest.raises(Duplicate):
            second.commit()


def test_concurrent_inserts_of_the_same_id_fail_the_second_commit(
    backend: MemoryContractBackend, shop: ShopId
) -> None:
    original = Widget.create(shop, "a")
    with backend.uow(shop) as first, backend.uow(shop) as second:
        widgets(first).add(original)
        widgets(second).add(Widget(original.id, shop, "clone"))
        first.commit()
        with pytest.raises(Duplicate):
            second.commit()


def test_update_after_insert_in_one_transaction_stays_an_insert(
    backend: MemoryContractBackend, shop: ShopId
) -> None:
    created = Widget.create(shop, "inséré puis modifié")
    with backend.uow(shop) as uow:
        widgets(uow).add(created)
        created.label = "modifié dans la même transaction"
        widgets(uow).update(created)  # reste une insertion au commit
        uow.commit()
    assert read_widget(backend, shop, created).version == 2
