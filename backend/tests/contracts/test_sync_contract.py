"""Contrat de la trace de synchronisation (T23) : aller-retour accepté et refusé, idempotence
par clé primaire (`Duplicate`), isolation des boutiques, événement du refus.

Rejoué sur l'adaptateur mémoire, sur SQLite (`tests/infrastructure/sqlalchemy`) et sur
PostgreSQL (`--backend=postgres`).
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.application.sync.ports import SyncOperationRepository
from app.domain.audit.values import Performer
from app.domain.sales.ids import SaleId
from app.domain.shared.errors import Duplicate
from app.domain.shared.ids import DeviceId, ShopId, UserId
from app.domain.sync.events import OfflineEntryRefused
from app.domain.sync.operation import SyncOperation, SyncOperationId, SyncOrigin, SyncStatus
from tests.contracts.backends import ContractBackend
from tests.contracts.helpers import run_in_uow

T = datetime(2026, 11, 11, 8, 0, tzinfo=UTC)
AUTHOR = UserId.new()
DEVICE = DeviceId.new()
ORIGIN = SyncOrigin(created_by=AUTHOR, device_id=DEVICE, captured_at=T, received_at=T)


def accepted(shop_id: ShopId, op_id: SyncOperationId | None = None) -> SyncOperation:
    return SyncOperation.accepted(
        op_id or SyncOperationId.new(),
        shop_id,
        op_type="sale.create",
        origin=ORIGIN,
        provisional_number="V-HL-3F2A-0007",
        entity_id=SaleId.new().value,
        number="V-000125",
    )


def rejected(shop_id: ShopId) -> SyncOperation:
    return SyncOperation.rejected(
        SyncOperationId.new(),
        shop_id,
        op_type="expense.create",
        origin=ORIGIN,
        provisional_number=None,
        error_code="FORBIDDEN",
        error_message="Refusé",
        performer=Performer(AUTHOR, "seller", DEVICE),
    )


def test_round_trip_and_isolation(backend: ContractBackend, shop_a: ShopId, shop_b: ShopId) -> None:
    ok, ko = accepted(shop_a), rejected(shop_a)
    assert [type(e) for e in ko.events] == [OfflineEntryRefused]
    with backend.uow(shop_a) as uow:
        SyncOperationRepository.within(uow).add(ok)
        SyncOperationRepository.within(uow).add(ko)
        uow.commit()
    with backend.uow(shop_a) as uow:
        found = SyncOperationRepository.within(uow).get(ok.id)
        refused = SyncOperationRepository.within(uow).get(ko.id)
    assert (found.status, found.number, found.entity_id) == (
        SyncStatus.ACCEPTED, "V-000125", ok.entity_id,
    )  # fmt: skip
    assert (found.origin, found.provisional_number, found.version) == (ORIGIN, "V-HL-3F2A-0007", 1)
    assert (refused.status, refused.error_code, refused.number) == (
        SyncStatus.REJECTED, "FORBIDDEN", None,
    )  # fmt: skip
    with backend.uow(shop_b) as uow:
        assert SyncOperationRepository.within(uow).find(ok.id) is None


def test_same_op_id_twice_is_a_duplicate(backend: ContractBackend, shop_a: ShopId) -> None:
    first = accepted(shop_a)
    run_in_uow(backend, shop_a, lambda uow: SyncOperationRepository.within(uow).add(first))
    again = accepted(shop_a, first.id)
    with pytest.raises(Duplicate):
        run_in_uow(backend, shop_a, lambda uow: SyncOperationRepository.within(uow).add(again))


def test_invariants() -> None:
    shop = ShopId.new()
    with pytest.raises(ValueError, match="acceptée"):
        SyncOperation(id=SyncOperationId.new(), shop_id=shop, op_type="sale.create",
                      origin=ORIGIN, status=SyncStatus.ACCEPTED)  # fmt: skip
    with pytest.raises(ValueError, match="refusée"):
        SyncOperation(id=SyncOperationId.new(), shop_id=shop, op_type="sale.create",
                      origin=ORIGIN, status=SyncStatus.REJECTED)  # fmt: skip
    with pytest.raises(ValueError, match="Type"):
        SyncOperation(id=SyncOperationId.new(), shop_id=shop, op_type="", origin=ORIGIN,
                      status=SyncStatus.REJECTED, error_code="X", error_message="m")  # fmt: skip
    with pytest.raises(TypeError):  # identifiant non typé : refus vérifié à dessein (ignore mypy)
        SyncOperation(id=uuid4(), shop_id=shop, op_type="x", origin=ORIGIN,  # type: ignore[arg-type]
                      status=SyncStatus.REJECTED, error_code="X", error_message="m")  # fmt: skip
