"""`AuditLog` mémoire : entrées immuables stockées comme des lignes en version 1, jamais réécrites.

L'entrée est une dataclass gelée : la stocker telle quelle suffit (aucune copie à protéger).
Aucune méthode ne passe par `MemoryTransaction.update` : l'ajout seul est structurel.
"""

from typing import cast

from app.application.audit.ports import AuditLog, AuditQuery, position
from app.application.ports.pagination import Page, PageRequest, paginate
from app.domain.audit.entry import AuditEntry
from app.infrastructure.persistence.memory.database import Row
from app.infrastructure.persistence.memory.shop_store import MemoryShopStore

STORED_VERSION = 1


class MemoryAuditLog(MemoryShopStore, AuditLog):
    table = "audit_entries"

    def _append(self, entry: AuditEntry) -> None:
        row = Row(
            shop_id=entry.shop_id,
            entity_id=entry.id,
            version=STORED_VERSION,
            unique={},
            payload=entry,
        )
        self._transaction.insert(self.table, row)

    def search(self, query: AuditQuery, page: PageRequest) -> Page[AuditEntry]:
        # Les lignes de cette table ne sont construites que par `_append`, à partir d'une entrée.
        entries = [cast(AuditEntry, row.payload) for row in self._transaction.rows(self.table)]
        ordered = sorted(
            (entry for entry in entries if query.matches(entry)), key=position, reverse=True
        )
        return paginate(ordered, page, position)
