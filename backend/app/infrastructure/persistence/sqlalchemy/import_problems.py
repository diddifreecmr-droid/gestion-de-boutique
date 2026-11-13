"""Rapport des lignes refusées d'un lot (`import_problem`, migration 0020, T35).

Posé une fois, dans la transaction de la confirmation (clé `(import_batch_id, position)` : un
second rapport du même lot échoue en `Duplicate`) ; jamais modifié. Insertion par paquets, sous
la limite de paramètres de SQLite et PostgreSQL (5 000 lignes refusées au plus par fichier).
"""

import sqlalchemy as sa

from app.application.imports.ports import ImportProblemLog
from app.domain.imports.ids import ImportBatchId
from app.domain.imports.problems import RowError
from app.infrastructure.persistence.errors import PRIMARY_KEY, duplicate
from app.infrastructure.persistence.sqlalchemy.shop_store import SqlShopStore
from app.infrastructure.persistence.sqlalchemy.tables_imports import import_problem

PROBLEMS_PER_INSERT = 1_000
"""6 paramètres par ligne : 6 000 par requête."""


class SqlImportProblemLog(SqlShopStore, ImportProblemLog):
    table = import_problem

    def _append(self, batch_id: ImportBatchId, problems: tuple[RowError, ...]) -> None:
        c = self.table.c
        taken = sa.select(c.position).where(self._own_shop(), c.import_batch_id == batch_id.value)
        if self._transaction.exists(taken):
            raise duplicate(self.table.name, PRIMARY_KEY)
        rows = [
            {
                "import_batch_id": batch_id.value,
                "position": position,
                "shop_id": self.shop_id.value,
                "line": problem.line,
                "column_name": problem.column,
                "message": problem.message,
            }
            for position, problem in enumerate(problems)
        ]
        for start in range(0, len(rows), PROBLEMS_PER_INSERT):
            self._transaction.write(
                sa.insert(self.table).values(rows[start : start + PROBLEMS_PER_INSERT])
            )

    def for_batch(self, batch_id: ImportBatchId) -> list[RowError]:
        c = self.table.c
        statement = (
            sa.select(self.table)
            .where(self._own_shop(), c.import_batch_id == batch_id.value)
            .order_by(c.position)
        )
        return [
            RowError(int(row["line"]), row["column_name"], row["message"])
            for row in self._transaction.fetch_all(statement)
        ]
