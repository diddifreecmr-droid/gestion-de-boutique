"""Contrat d'unicité : identifiant et clés déclarées (`UniqueKey`) → `Duplicate`.

`run_in_uow` accepte que l'adaptateur lève à l'écriture **ou** au commit : seul compte que
rien ne soit écrit.
"""

import pytest

from app.application.ports.uow import UnitOfWork
from app.domain.shared.errors import Duplicate, NotFound
from app.domain.shared.ids import ShopId
from tests.contracts.backends import ContractBackend
from tests.contracts.helpers import committed_widget, read_widget, run_in_uow, widgets
from tests.contracts.widget import Widget


def test_same_code_twice_in_a_shop_is_a_duplicate(backend: ContractBackend, shop_a: ShopId) -> None:
    committed_widget(backend, shop_a, "premier", code="CH-42")
    rival = Widget.create(shop_a, "second", code="CH-42")
    with pytest.raises(Duplicate) as caught:
        run_in_uow(backend, shop_a, lambda uow: widgets(uow).add(rival))
    assert caught.value.details["constraint"] == "widget_code"
    assert rival.version == 0
    with backend.uow(shop_a) as uow, pytest.raises(NotFound):
        widgets(uow).get(rival.id)


def test_duplicate_within_one_transaction(backend: ContractBackend, shop_a: ShopId) -> None:
    first = Widget.create(shop_a, "a", code="X")

    def add_both(uow: UnitOfWork) -> None:
        widgets(uow).add(first)
        widgets(uow).add(Widget.create(shop_a, "b", code="X"))

    with pytest.raises(Duplicate):
        run_in_uow(backend, shop_a, add_both)
    with backend.uow(shop_a) as uow, pytest.raises(NotFound):
        widgets(uow).get(first.id)  # tout ou rien : le premier n'est pas écrit non plus


def test_same_code_in_two_shops_is_allowed(
    backend: ContractBackend, shop_a: ShopId, shop_b: ShopId
) -> None:
    in_a = committed_widget(backend, shop_a, code="CH-42")
    in_b = committed_widget(backend, shop_b, code="CH-42")
    assert read_widget(backend, shop_a, in_a).code == read_widget(backend, shop_b, in_b).code


def test_none_is_not_constrained(backend: ContractBackend, shop_a: ShopId) -> None:
    first = committed_widget(backend, shop_a, "sans code 1")
    second = committed_widget(backend, shop_a, "sans code 2")
    assert read_widget(backend, shop_a, first).code is read_widget(backend, shop_a, second).code


def test_update_into_a_taken_code_is_a_duplicate(backend: ContractBackend, shop_a: ShopId) -> None:
    committed_widget(backend, shop_a, code="PRIS")
    other = committed_widget(backend, shop_a, code="LIBRE")
    other.code = "PRIS"
    with pytest.raises(Duplicate):
        run_in_uow(backend, shop_a, lambda uow: widgets(uow).update(other))
    assert other.version == 1
    assert read_widget(backend, shop_a, other).code == "LIBRE"


def test_keeping_its_own_code_on_update_is_fine(backend: ContractBackend, shop_a: ShopId) -> None:
    widget = committed_widget(backend, shop_a, code="MIEN")
    widget.label = "renommé"
    run_in_uow(backend, shop_a, lambda uow: widgets(uow).update(widget))
    assert read_widget(backend, shop_a, widget).version == 2


def test_freed_code_can_be_reused(backend: ContractBackend, shop_a: ShopId) -> None:
    widget = committed_widget(backend, shop_a, code="TOURNANT")
    widget.code = None
    run_in_uow(backend, shop_a, lambda uow: widgets(uow).update(widget))
    reuser = committed_widget(backend, shop_a, code="TOURNANT")
    assert read_widget(backend, shop_a, reuser).code == "TOURNANT"


@pytest.mark.parametrize("same_shop", [True, False], ids=["même boutique", "autre boutique"])
def test_reusing_an_existing_id_is_a_duplicate(
    backend: ContractBackend, shop_a: ShopId, shop_b: ShopId, same_shop: bool
) -> None:
    original = committed_widget(backend, shop_a, "original")
    shop = shop_a if same_shop else shop_b  # identifiant global (clé primaire)
    clone = Widget(original.id, shop, "clone")
    with pytest.raises(Duplicate):
        run_in_uow(backend, shop, lambda uow: widgets(uow).add(clone))
    assert clone.version == 0
    assert read_widget(backend, shop_a, original).label == "original"
