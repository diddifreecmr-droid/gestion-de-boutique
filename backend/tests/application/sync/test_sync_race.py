"""`SyncOperations` : course entre deux envois du même `op_id` (la trace concurrente fait
foi), garde d'une trace introuvable, garde d'un type sans exécutant (fail-fast)."""

from collections.abc import Mapping
from datetime import UTC, datetime

import pytest

from app.application.expenses.references import ExpenseInput
from app.application.plans.ports import Entitlements
from app.application.sales.inputs import SaleInput
from app.application.security.actor import Actor
from app.application.security.roles import Role
from app.application.shops.context import actor_shop
from app.application.sync.inputs import (
    OperationDecoder,
    OperationInput,
    Outcome,
    ResultStatus,
    SyncBatch,
)
from app.application.sync.ports import SyncOperationRepository
from app.application.sync.runner import OperationRunner, operation_type
from app.application.sync.use_cases.sync_operations import SyncOperations
from app.bootstrap.persistence import MEMORY_REPOSITORIES
from app.domain.plans.entitlements import Entitlement
from app.domain.shared.ids import DeviceId, ShopId, UserId
from app.domain.sync.operation import SyncOperation, SyncOperationId, SyncOrigin
from app.infrastructure.persistence.memory.clock import FixedClock
from app.infrastructure.persistence.memory.database import MemoryDatabase
from app.infrastructure.persistence.memory.uow import MemoryUnitOfWorkFactory

T = datetime(2026, 11, 11, 8, 0, tzinfo=UTC)


class Open(Entitlements):
    def is_enabled(self, shop_id: ShopId, entitlement: Entitlement) -> bool:
        return True


class Unused:
    def sale(self, op_id: SyncOperationId, payload: Mapping[str, object]) -> SaleInput:
        raise AssertionError

    def expense(self, op_id: SyncOperationId, payload: Mapping[str, object]) -> ExpenseInput:
        raise AssertionError


class Racing(OperationRunner):
    """Simule un envoi concurrent : la trace du même `op_id` est écrite pendant l'exécution."""

    def __init__(self, uows: MemoryUnitOfWorkFactory, *, write: bool) -> None:
        self._uows, self._write = uows, write

    def run(self, actor: Actor, operation: OperationInput, decoder: OperationDecoder) -> Outcome:
        if self._write:
            origin = SyncOrigin(created_by=actor.user_id, device_id=actor.device_id,
                                captured_at=T, received_at=T)  # fmt: skip
            trace = SyncOperation.accepted(
                operation.op_id, actor_shop(actor), op_type=operation.type, origin=origin,
                provisional_number=None, entity_id=operation.op_id.value, number="V-000009",
            )  # fmt: skip
            with self._uows(trace.shop_id) as uow:
                SyncOperationRepository.within(uow).add(trace)
                uow.commit()
        return Outcome(entity_id=operation.op_id.value, number="V-000009", created=True)


def setup(*, write: bool) -> tuple[SyncOperations, Actor, OperationInput]:
    uows = MemoryUnitOfWorkFactory(MemoryDatabase(), MEMORY_REPOSITORIES, ())
    actor = Actor(user_id=UserId.new(), device_id=DeviceId.new(), shop_id=ShopId.new(),
                  role=Role.SELLER)  # fmt: skip
    use_case = SyncOperations(uows, Open(), Racing(uows, write=write), FixedClock(T))
    operation = OperationInput(op_id=SyncOperationId.new(), type="sale.create", captured_at=T)
    return use_case, actor, operation


def test_concurrent_trace_wins_and_is_replayed_as_duplicate() -> None:
    use_case, actor, operation = setup(write=True)
    [result] = use_case.execute(actor, SyncBatch(device_id=actor.device_id,
                                                 operations=(operation,)), Unused())  # fmt: skip
    assert (result.status, result.number) == (ResultStatus.DUPLICATE, "V-000009")


def test_lot_2_guard_and_unknown_type() -> None:
    assert operation_type("sale.create").value == "sale.create"
    with pytest.raises(Exception, match="Lot 2"):
        operation_type("trip_expense.create")
