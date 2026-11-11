"""Unité de travail de boutique **jointe** à une unité plateforme mémoire, et validation commune.

Pendant mémoire de la transaction SQL partagée (voir `application/identity/uow.py`) :

- l'unité jointe écrit dans sa propre `MemoryTransaction`, **inscrite** auprès de l'unité
  plateforme ; son `commit()` remet ses événements à ses handlers mais ne valide rien ;
- l'unité plateforme valide ses écritures et celles de toutes ses unités jointes **en un seul
  bloc** (`apply_jointly`) : sous les verrous des deux stockages, tout est préparé et vérifié
  (versions, identifiants, unicité, séquences), puis tout est installé — ou rien ;
- une unité jointe qui jette des écritures (exception, oubli de `commit()`) **condamne**
  l'unité plateforme : elle ne pourra plus rien valider (`UnitOfWorkStateError`).

Ordre des verrous : base de boutique puis stockage plateforme, toujours ; aucun autre code ne
tient les deux à la fois : pas d'interblocage.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from app.application.ports.errors import UnitOfWorkStateError
from app.application.ports.event_handler import EventHandler
from app.domain.shared.ids import ShopId
from app.infrastructure.persistence.memory.database import ChangeSet, MemoryDatabase, Staged
from app.infrastructure.persistence.memory.platform_store import MemoryPlatformStore, PlatformWrite
from app.infrastructure.persistence.memory.transaction import MemoryTransaction
from app.infrastructure.persistence.memory.uow import MemoryUnitOfWork, RepositoryRegistry


@dataclass(frozen=True, slots=True)
class ShopJoin:
    """Ce qu'il faut pour joindre des unités de boutique : base, dépôts, handlers de boutique."""

    database: MemoryDatabase
    repositories: RepositoryRegistry
    handlers: Sequence[EventHandler] = ()


class JointHost(Protocol):
    """L'unité plateforme vue par ses unités jointes."""

    def enlist(self, transaction: MemoryTransaction) -> None: ...

    def doom(self) -> None: ...


class JoinedMemoryUnitOfWork(MemoryUnitOfWork):
    def __init__(self, join: ShopJoin, shop_id: ShopId, host: JointHost) -> None:
        super().__init__(
            join.database, shop_id, repositories=join.repositories, handlers=join.handlers
        )
        self._host = host

    def _begin(self) -> None:
        super()._begin()
        self._host.enlist(self._require_transaction())

    def _commit(self) -> None:
        """Rien n'est validé ici : l'unité plateforme validera cette transaction avec la sienne."""

    def _rollback(self) -> None:
        """Écritures jetées : si elles existaient, la transaction commune est condamnée.

        Une sortie sans écriture (lecture seule) ne condamne rien.
        """
        transaction = self._require_transaction()
        wrote = transaction.has_changes
        transaction.discard()
        if wrote:
            self._host.doom()


def apply_jointly(
    database: MemoryDatabase,
    store: MemoryPlatformStore,
    shop_changes: Sequence[ChangeSet],
    platform_writes: list[PlatformWrite],
) -> None:
    """Valide tout d'un bloc ; lève sans rien installer au premier conflit."""
    with database.locked(), store.locked():
        staged: Staged | None = None
        for changes in shop_changes:
            staged = database.stage(changes, onto=staged)
        staged_platform = store.stage(platform_writes)
        if staged is not None:
            database.install(staged)
        store.install(staged_platform)


def require_alive(doomed: bool) -> None:
    if doomed:
        msg = "Une unité de boutique jointe a échoué : la transaction entière est annulée"
        raise UnitOfWorkStateError(msg)


__all__ = [
    "JoinedMemoryUnitOfWork",
    "ShopJoin",
    "apply_jointly",
    "require_alive",
]
