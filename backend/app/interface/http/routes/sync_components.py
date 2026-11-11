"""Cas d'utilisation de la synchronisation hors connexion, assemblés par la composition root."""

from dataclasses import dataclass

from app.application.sync.use_cases.offline_snapshot import ReadOfflineSnapshot
from app.application.sync.use_cases.sync_operations import SyncOperations
from app.interface.http.security import AuthGuard


@dataclass(frozen=True, slots=True, kw_only=True)
class SyncComponents:
    sync: SyncOperations
    snapshot: ReadOfflineSnapshot
    guard: AuthGuard
