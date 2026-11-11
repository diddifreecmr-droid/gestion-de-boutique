"""Contrat de l'unité de travail : visibilité au commit, rollback, cycle de vie strict."""

import pytest

from app.application.ports.errors import UncommittedChanges, UnitOfWorkStateError
from app.application.ports.uow import UnitOfWork
from app.domain.shared.errors import NotFound
from app.domain.shared.ids import ShopId
from tests.contracts.backends import ContractBackend
from tests.contracts.helpers import committed_widget, read_widget, run_in_uow, widgets
from tests.contracts.widget import Widget


class Boom(Exception):
    """Exception métier quelconque levée au milieu d'un cas d'utilisation."""


def test_writes_are_invisible_to_other_uows_until_commit(
    backend: ContractBackend, shop_a: ShopId
) -> None:
    widget = Widget.create(shop_a, "en cours")
    with backend.uow(shop_a) as writer:
        widgets(writer).add(widget)
        assert widgets(writer).get(widget.id).label == "en cours"  # visible pour soi-même
        with backend.uow(shop_a) as reader, pytest.raises(NotFound):
            widgets(reader).get(widget.id)
        writer.commit()
    assert read_widget(backend, shop_a, widget).label == "en cours"


def test_explicit_rollback_discards_everything(backend: ContractBackend, shop_a: ShopId) -> None:
    existing = committed_widget(backend, shop_a, "intact")
    added = Widget.create(shop_a, "jamais écrit")
    with backend.uow(shop_a) as uow:
        loaded = widgets(uow).get(existing.id)
        loaded.rename("modifié")
        widgets(uow).update(loaded)
        widgets(uow).add(added)
        uow.rollback()
    stored = read_widget(backend, shop_a, existing)
    assert (stored.label, stored.version) == ("intact", 1)
    with backend.uow(shop_a) as uow, pytest.raises(NotFound):
        widgets(uow).get(added.id)


def test_exception_rolls_back_and_is_reraised(backend: ContractBackend, shop_a: ShopId) -> None:
    existing = committed_widget(backend, shop_a, "intact")
    added = Widget.create(shop_a, "jamais écrit")

    def use_case(uow: UnitOfWork) -> None:
        widgets(uow).add(added)
        loaded = widgets(uow).get(existing.id)
        loaded.rename("modifié")
        widgets(uow).update(loaded)
        raise Boom

    with pytest.raises(Boom):
        run_in_uow(backend, shop_a, use_case)
    assert read_widget(backend, shop_a, existing).label == "intact"
    with backend.uow(shop_a) as uow, pytest.raises(NotFound):
        widgets(uow).get(added.id)


def test_exit_without_commit_after_writes_fails_loudly(
    backend: ContractBackend, shop_a: ShopId
) -> None:
    widget = Widget.create(shop_a, "oublié")
    with pytest.raises(UncommittedChanges), backend.uow(shop_a) as uow:
        widgets(uow).add(widget)
    with backend.uow(shop_a) as uow, pytest.raises(NotFound):
        widgets(uow).get(widget.id)


def test_read_only_uow_needs_no_commit(backend: ContractBackend, shop_a: ShopId) -> None:
    widget = committed_widget(backend, shop_a)
    assert read_widget(backend, shop_a, widget).version == 1


def test_commit_twice_is_an_error(backend: ContractBackend, shop_a: ShopId) -> None:
    with backend.uow(shop_a) as uow:
        uow.commit()
        with pytest.raises(UnitOfWorkStateError, match="COMMITTED"):
            uow.commit()
        with pytest.raises(UnitOfWorkStateError):
            uow.rollback()


def test_commit_after_rollback_is_an_error(backend: ContractBackend, shop_a: ShopId) -> None:
    with backend.uow(shop_a) as uow:
        uow.rollback()
        with pytest.raises(UnitOfWorkStateError, match="ROLLED_BACK"):
            uow.commit()
        with pytest.raises(UnitOfWorkStateError):
            uow.rollback()


def test_uow_is_single_use_and_needs_with(backend: ContractBackend, shop_a: ShopId) -> None:
    uow = backend.uow(shop_a)
    with pytest.raises(UnitOfWorkStateError, match="NEW"):
        uow.commit()
    with pytest.raises(UnitOfWorkStateError, match="hors transaction"):
        widgets(uow)
    with pytest.raises(UnitOfWorkStateError):
        _ = uow.numbering
    with uow:
        uow.commit()
    with pytest.raises(UnitOfWorkStateError, match="une fois"), uow:
        pass  # entrée refusée : le corps n'est jamais exécuté


def test_repository_is_unusable_after_the_transaction(
    backend: ContractBackend, shop_a: ShopId
) -> None:
    widget = committed_widget(backend, shop_a)
    with backend.uow(shop_a) as uow:
        repository = widgets(uow)
        uow.commit()
    with pytest.raises(UnitOfWorkStateError):
        repository.get(widget.id)


def test_uow_exposes_its_shop_and_one_repository_per_port(
    backend: ContractBackend, shop_a: ShopId
) -> None:
    with backend.uow(shop_a) as uow:
        assert uow.shop_id == shop_a
        assert widgets(uow) is widgets(uow)
        assert widgets(uow).shop_id == shop_a
