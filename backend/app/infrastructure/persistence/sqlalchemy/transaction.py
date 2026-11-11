"""Transaction SQL d'une unité de travail : une connexion du pool, une transaction de base.

Chaque écriture s'exécute dans un **savepoint** : si elle viole une contrainte, seule cette
écriture est annulée et la transaction reste utilisable (sur PostgreSQL, une erreur annule
sinon toute la transaction). C'est le comportement de l'adaptateur mémoire, qui refuse
l'écriture sans rien abîmer : l'appelant peut traduire l'erreur et poursuivre.
"""

from typing import Any

import sqlalchemy as sa
from sqlalchemy.sql.dml import Delete, Insert, Update

from app.application.ports.errors import UnitOfWorkStateError

Write = Insert | Update | Delete


class SqlTransaction:
    """Ouverte à la construction ; `commit()` ou `discard()` la ferment et rendent la connexion."""

    def __init__(self, engine: sa.Engine) -> None:
        self._connection = engine.connect()
        try:
            self._transaction = self._connection.begin()
        except BaseException:
            self._connection.close()
            raise
        self._closed = False
        self._writes = 0

    # ------------------------------------------------------------------ lecture
    def fetch_one(self, statement: sa.Select[Any]) -> sa.RowMapping | None:
        """Première ligne de `statement` (ou `None`)."""
        self._require_open()
        return self._connection.execute(statement).mappings().first()

    def fetch_all(self, statement: sa.Select[Any]) -> list[sa.RowMapping]:
        """Toutes les lignes de `statement`, dans l'ordre de la requête."""
        self._require_open()
        return list(self._connection.execute(statement).mappings().all())

    def exists(self, statement: sa.Select[Any]) -> bool:
        return self.fetch_one(statement.limit(1)) is not None

    # ------------------------------------------------------------------ écriture
    def write(self, statement: Write) -> int:
        """Exécute `statement` dans un savepoint ; renvoie le nombre de lignes touchées.

        En cas d'erreur, le savepoint est annulé puis l'erreur SQLAlchemy est relancée telle
        quelle : la traduire (`IntegrityError` → `Duplicate`…) revient à l'appelant.
        """
        self._require_open()
        with self._connection.begin_nested():
            count = self._connection.execute(statement).rowcount
        if count:
            self._writes += 1
        return count

    # ------------------------------------------------------------------ fin
    @property
    def has_changes(self) -> bool:
        """Vrai si une écriture a touché au moins une ligne (rien n'est encore validé)."""
        return self._writes > 0

    @property
    def write_count(self) -> int:
        """Écritures ayant touché au moins une ligne (unités jointes : « ai-je écrit ? »)."""
        return self._writes

    @property
    def is_open(self) -> bool:
        return not self._closed

    def commit(self) -> None:
        self._require_open()
        self._closed = True
        try:
            self._transaction.commit()
        finally:
            self._connection.close()

    def discard(self) -> None:
        """Rollback (y compris après un `commit` en échec) ; rend la connexion au pool."""
        self._closed = True
        try:
            if self._transaction.is_active:
                self._transaction.rollback()
        finally:
            self._connection.close()

    def _require_open(self) -> None:
        if self._closed:
            msg = "Transaction SQL déjà validée ou annulée"
            raise UnitOfWorkStateError(msg)
