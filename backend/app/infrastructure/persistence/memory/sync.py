"""Adaptateur mémoire de la synchronisation hors connexion (T23) : traces `sync_operation`."""

from app.application.sync.ports import SyncOperationRepository
from app.domain.sync.operation import SyncOperation, SyncOperationId
from app.infrastructure.persistence.memory.repository import MemoryRepository


class MemorySyncOperationRepository(
    MemoryRepository[SyncOperationId, SyncOperation], SyncOperationRepository
):
    table = "sync_operations"


MEMORY_SYNC_REPOSITORIES = (MemorySyncOperationRepository,)
