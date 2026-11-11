"""Adaptateur SQL de la synchronisation hors connexion (T23) : table `sync_operation`."""

from typing import Any

import sqlalchemy as sa

from app.application.sync.ports import SyncOperationRepository
from app.domain.shared.ids import DeviceId, ShopId, UserId
from app.domain.sync.operation import SyncOperation, SyncOperationId, SyncOrigin, SyncStatus
from app.infrastructure.persistence.sqlalchemy.columns import from_db, to_db
from app.infrastructure.persistence.sqlalchemy.repository import SqlRepository
from app.infrastructure.persistence.sqlalchemy.tables_sync import sync_operation


class SqlSyncOperationRepository(
    SqlRepository[SyncOperationId, SyncOperation], SyncOperationRepository
):
    table = sync_operation

    def _to_columns(self, aggregate: SyncOperation) -> dict[str, Any]:
        origin = aggregate.origin
        return {
            "op_type": aggregate.op_type,
            "status": aggregate.status.value,
            "provisional_number": aggregate.provisional_number,
            "created_by": origin.created_by.value,
            "device_id": origin.device_id.value,
            "captured_at": to_db(origin.captured_at),
            "received_at": to_db(origin.received_at),
            "entity_id": aggregate.entity_id,
            "number": aggregate.number,
            "error_code": aggregate.error_code,
            "error_message": aggregate.error_message,
        }

    def _from_row(self, row: sa.RowMapping) -> SyncOperation:
        return SyncOperation(
            id=SyncOperationId(row["id"]),
            shop_id=ShopId(row["shop_id"]),
            op_type=row["op_type"],
            origin=SyncOrigin(
                created_by=UserId(row["created_by"]),
                device_id=DeviceId(row["device_id"]),
                captured_at=from_db(row["captured_at"]),
                received_at=from_db(row["received_at"]),
            ),
            status=SyncStatus(row["status"]),
            provisional_number=row["provisional_number"],
            entity_id=row["entity_id"],
            number=row["number"],
            error_code=row["error_code"],
            error_message=row["error_message"],
            version=int(row["version"]),
        )


SQL_SYNC_REPOSITORIES = (SqlSyncOperationRepository,)
