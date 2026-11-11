"""Mémoire : registre des dépôts, fabrique d'unités de travail, garde-fous de construction."""

from typing import Any

import pytest

from app.application.ports.errors import IsolationViolation, UnitOfWorkStateError
from app.application.ports.repository import Repository
from app.application.ports.shop_bound import ShopBoundPort
from app.application.ports.uow import UnitOfWorkFactory
from app.domain.shared.ids import ShopId, UserId
from app.infrastructure.persistence.memory.database import MemoryDatabase
from app.infrastructure.persistence.memory.repository import MemoryRepository
from app.infrastructure.persistence.memory.transaction import MemoryTransaction
from app.infrastructure.persistence.memory.uow import (
    MemoryAdapter,
    MemoryUnitOfWork,
    MemoryUnitOfWorkFactory,
)
from tests.contracts.backends.memory import REGISTRY, MemoryWidgetRepository
from tests.contracts.handlers import RecordingHandler
from tests.contracts.widget import Widget, WidgetId, WidgetRepository

SHOP = ShopId.new()


class NoTableRepository(MemoryRepository[WidgetId, Widget], WidgetRepository):
    """Oublie de déclarer `table`."""


class SecondWidgetRepository(MemoryWidgetRepository):
    table = "widgets_bis"


def memory_uow(*adapters: MemoryAdapter) -> MemoryUnitOfWork:
    return MemoryUnitOfWork(MemoryDatabase(), SHOP, repositories=adapters)


def test_factory_builds_uows_sharing_one_database() -> None:
    recorder = RecordingHandler()
    factory: UnitOfWorkFactory = MemoryUnitOfWorkFactory(MemoryDatabase(), REGISTRY, [recorder])
    widget = Widget.create(SHOP, "partagé")
    with factory(SHOP) as uow:
        WidgetRepository.within(uow).add(widget)
        uow.commit()
    with factory(SHOP) as uow:
        assert WidgetRepository.within(uow).get(widget.id).label == "partagé"
    assert len(recorder.received) == 1


def test_unregistered_port_is_a_lookup_error() -> None:
    with memory_uow() as uow, pytest.raises(LookupError, match="WidgetRepository"):
        WidgetRepository.within(uow)


def test_ambiguous_registry_is_a_lookup_error() -> None:
    adapters = (MemoryWidgetRepository, SecondWidgetRepository)
    with memory_uow(*adapters) as uow, pytest.raises(LookupError, match="un et un seul"):
        WidgetRepository.within(uow)


def test_within_refuses_an_adapter_of_another_port() -> None:
    class WrongProvider:
        def repository_for(self, port: type[ShopBoundPort]) -> ShopBoundPort:
            with memory_uow(*REGISTRY) as uow:
                return WidgetRepository.within(uow)

    class OtherPort(Repository[WidgetId, Widget]):
        pass

    with pytest.raises(TypeError, match="n'implémente pas"):
        OtherPort.within(WrongProvider())


def test_repository_must_declare_its_table() -> None:
    with memory_uow(*REGISTRY) as uow, pytest.raises(TypeError, match="table"):
        NoTableRepository(SHOP, uow, MemoryTransaction(MemoryDatabase(), SHOP))


def test_shop_id_type_is_enforced() -> None:
    not_a_shop: Any = UserId.new()  # refus à l'exécution d'un identifiant d'un autre type
    with pytest.raises(TypeError, match="ShopId"):
        MemoryUnitOfWork(MemoryDatabase(), not_a_shop, repositories=())
    with memory_uow(*REGISTRY) as uow, pytest.raises(TypeError, match="ShopId"):
        MemoryWidgetRepository(not_a_shop, uow, MemoryTransaction(MemoryDatabase(), SHOP))


def test_adapter_hooks_refuse_use_before_begin() -> None:
    uow = memory_uow(*REGISTRY)
    with pytest.raises(UnitOfWorkStateError, match="non ouverte"):
        uow._numbering()  # primitive d'adaptateur appelée hors cycle : garde-fou testé
    with pytest.raises(UnitOfWorkStateError, match="non ouverte"):
        uow._has_pending_changes()


def test_load_returning_another_shop_is_detected() -> None:
    other_shop = ShopId.new()

    class LeakyRepository(MemoryWidgetRepository):
        def _load(self, entity_id: WidgetId) -> Widget | None:
            return Widget(entity_id, other_shop, "fuite", version=1)

    with (
        memory_uow(LeakyRepository) as uow,
        pytest.raises(IsolationViolation, match="autre boutique"),
    ):
        WidgetRepository.within(uow).get(WidgetId.new())


class PlainRepository(Repository[WidgetId, Widget]):
    """Port sans contrainte d'unicité (valeur par défaut du gabarit)."""


class MemoryPlainRepository(MemoryRepository[WidgetId, Widget], PlainRepository):
    table = "plain"


def test_tables_are_independent_and_unique_keys_default_to_none() -> None:
    with memory_uow(MemoryWidgetRepository, MemoryPlainRepository) as uow:
        WidgetRepository.within(uow).add(Widget.create(SHOP, "a", code="X"))
        plain = PlainRepository.within(uow)
        assert plain.unique_keys() == ()
        plain.add(Widget.create(SHOP, "b", code="X"))  # autre table, aucune contrainte
        plain.add(Widget.create(SHOP, "c", code="X"))
        uow.commit()
