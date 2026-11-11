"""Contrat du dépôt lié à une boutique : CRUD, isolation (B ne voit jamais A), verrou optimiste."""

import pytest

from app.application.ports.errors import IsolationViolation
from app.domain.shared.errors import NotFound, VersionConflict
from app.domain.shared.ids import ShopId
from tests.contracts.backends import ContractBackend
from tests.contracts.helpers import committed_widget, read_widget, run_in_uow, widgets
from tests.contracts.widget import Widget, WidgetId


def test_add_then_get_returns_a_copy_in_version_1(backend: ContractBackend, shop_a: ShopId) -> None:
    widget = committed_widget(backend, shop_a, "pédale", code="P-1")
    assert widget.version == 1
    stored = read_widget(backend, shop_a, widget)
    assert stored is not widget
    assert (stored.id, stored.shop_id, stored.label, stored.code, stored.version) == (
        widget.id,
        shop_a,
        "pédale",
        "P-1",
        1,
    )
    assert len(stored.events) == 0  # les événements ne sont pas persistés avec l'état


def test_update_persists_and_increments_version(backend: ContractBackend, shop_a: ShopId) -> None:
    widget = committed_widget(backend, shop_a, "avant")
    with backend.uow(shop_a) as uow:
        loaded = widgets(uow).get(widget.id)
        loaded.rename("après")
        widgets(uow).update(loaded)
        assert loaded.version == 2
        loaded.rename("encore")
        widgets(uow).update(loaded)  # deux mises à jour dans la même transaction
        uow.commit()
    stored = read_widget(backend, shop_a, widget)
    assert (stored.label, stored.version) == ("encore", 3)


def test_caller_mutation_never_leaks_into_storage(backend: ContractBackend, shop_a: ShopId) -> None:
    widget = committed_widget(backend, shop_a, "original")
    widget.label = "modifié sans update"
    assert read_widget(backend, shop_a, widget).label == "original"


def test_get_unknown_id_raises_not_found(backend: ContractBackend, shop_a: ShopId) -> None:
    unknown = WidgetId.new()
    with backend.uow(shop_a) as uow, pytest.raises(NotFound) as caught:
        widgets(uow).get(unknown)
    assert caught.value.details == {"id": str(unknown)}


def test_shop_b_never_reads_shop_a(
    backend: ContractBackend, shop_a: ShopId, shop_b: ShopId
) -> None:
    widget = committed_widget(backend, shop_a)
    with backend.uow(shop_b) as uow, pytest.raises(NotFound) as cross_shop:
        widgets(uow).get(widget.id)
    with backend.uow(shop_b) as uow, pytest.raises(NotFound) as absent:
        widgets(uow).get(WidgetId.new())
    # Même erreur, même message : rien ne distingue « autre boutique » d'« inexistant ».
    assert cross_shop.value.message == absent.value.message
    assert set(cross_shop.value.details) == set(absent.value.details) == {"id"}


def test_shop_b_cannot_update_shop_a_by_reusing_its_id(
    backend: ContractBackend, shop_a: ShopId, shop_b: ShopId
) -> None:
    original = committed_widget(backend, shop_a, "à A")
    forged = Widget(original.id, shop_b, "piraté", version=1)
    with backend.uow(shop_b) as uow, pytest.raises(NotFound):
        widgets(uow).update(forged)
    assert forged.version == 1  # l'échec ne fausse pas la version de l'appelant
    assert read_widget(backend, shop_a, original).label == "à A"


def test_aggregate_of_another_shop_is_an_isolation_bug(
    backend: ContractBackend, shop_a: ShopId, shop_b: ShopId
) -> None:
    stored_in_a = committed_widget(backend, shop_a)
    with backend.uow(shop_b) as uow:
        with pytest.raises(IsolationViolation):
            widgets(uow).add(Widget.create(shop_a, "intrus"))
        with pytest.raises(IsolationViolation):
            widgets(uow).update(stored_in_a)


def test_stale_version_raises_version_conflict(backend: ContractBackend, shop_a: ShopId) -> None:
    widget = committed_widget(backend, shop_a, "v1")
    stale = read_widget(backend, shop_a, widget)
    fresh = read_widget(backend, shop_a, widget)
    fresh.rename("v2 gagnante")
    run_in_uow(backend, shop_a, lambda uow: widgets(uow).update(fresh))
    stale.rename("v2 perdante")
    with pytest.raises(VersionConflict):
        run_in_uow(backend, shop_a, lambda uow: widgets(uow).update(stale))
    assert stale.version == 1
    stored = read_widget(backend, shop_a, widget)
    assert (stored.label, stored.version) == ("v2 gagnante", 2)


def test_update_of_never_added_aggregate_is_refused(
    backend: ContractBackend, shop_a: ShopId
) -> None:
    with backend.uow(shop_a) as uow, pytest.raises(ValueError, match="version"):
        widgets(uow).update(Widget.create(shop_a, "neuf"))


def test_add_of_already_stored_aggregate_is_refused(
    backend: ContractBackend, shop_a: ShopId
) -> None:
    widget = committed_widget(backend, shop_a)
    with backend.uow(shop_a) as uow, pytest.raises(ValueError, match="neuf"):
        widgets(uow).add(widget)
