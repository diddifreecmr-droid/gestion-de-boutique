"""Numérotation SQL continue et sans trou : table `document_counter` (RG-T05, TR-10, A8).

Mécanisme (portable, aucun SQL propre à un moteur) : **incrément atomique** dans la
transaction de l'unité de travail,

    UPDATE document_counter SET last_value = last_value + 1, version = version + 1
     WHERE shop_id = :shop AND doc_type = :type

puis relecture de `last_value`. L'`UPDATE` pose un verrou de ligne tenu jusqu'à la fin de la
transaction : une transaction concurrente sur le même compteur **attend**, puis repart de la
valeur validée (lecture validée : l'expression `last_value + 1` est réévaluée sur la ligne à
jour). Un rollback rend le verrou sans rien consommer ; deux transactions n'obtiennent donc
jamais le même numéro, et aucun numéro validé n'est sauté.

Pourquoi pas « lire, puis `UPDATE … WHERE version = :lue` + réessai » ? Sous verrou de ligne,
le perdant attend de toute façon le gagnant, puis échoue et doit relire : sous 20 ventes
concurrentes un même appelant peut perdre jusqu'à 19 fois. L'incrément atomique obtient la même
garantie sans réessai ni borne arbitraire. La colonne `version` est tout de même incrémentée,
pour rester cohérente avec la convention de verrou optimiste (specs § 5.1).

Première attribution d'un couple (boutique, type) : `INSERT` à 1, dans un savepoint. Si une
transaction concurrente a créé la ligne entre-temps (clé primaire prise), on incrémente la
sienne — une seule reprise, bornée ; tout autre échec remonte.
"""

import sqlalchemy as sa

from app.application.ports.numbering import DocumentNumberAllocator
from app.domain.shared.doc_number import DocNumber, DocType
from app.domain.shared.ids import ShopId
from app.infrastructure.persistence.sqlalchemy.tables import document_counter
from app.infrastructure.persistence.sqlalchemy.transaction import SqlTransaction

FIRST_NUMBER = 1


class SqlDocumentNumberAllocator(DocumentNumberAllocator):
    """Compteurs de la boutique de l'unité de travail, dans sa transaction."""

    def __init__(self, transaction: SqlTransaction, shop_id: ShopId) -> None:
        self._transaction = transaction
        self._shop_id = shop_id

    def next(self, doc_type: DocType) -> DocNumber:
        if not isinstance(doc_type, DocType):
            msg = f"doc_type doit être un DocType, reçu {doc_type!r}"
            raise TypeError(msg)
        if not self._increment(doc_type):
            if self._create(doc_type):
                return DocNumber(doc_type, FIRST_NUMBER)
            if not self._increment(doc_type):  # créée par une transaction concurrente
                msg = f"Compteur {doc_type.value} ni incrémentable ni créable"
                raise RuntimeError(msg)
        row = self._transaction.fetch_one(
            sa.select(document_counter.c.last_value).where(self._key(doc_type))
        )
        if row is None:  # impossible : la ligne est verrouillée par cette transaction
            msg = f"Compteur {doc_type.value} disparu après incrément"
            raise RuntimeError(msg)
        return DocNumber(doc_type, int(row["last_value"]))

    def _increment(self, doc_type: DocType) -> bool:
        statement = (
            sa.update(document_counter)
            .where(self._key(doc_type))
            .values(
                last_value=document_counter.c.last_value + 1,
                version=document_counter.c.version + 1,
            )
        )
        return self._transaction.write(statement) == 1

    def _create(self, doc_type: DocType) -> bool:
        """Crée le compteur à 1 ; `False` si la clé primaire vient d'être prise par un autre."""
        statement = sa.insert(document_counter).values(
            shop_id=self._shop_id.value,
            doc_type=doc_type.value,
            last_value=FIRST_NUMBER,
            version=1,
        )
        try:
            self._transaction.write(statement)
        except sa.exc.IntegrityError:
            # Seule cause attendue : création concurrente. Vérifié aussitôt par l'appelant,
            # dont l'incrément échoue bruyamment (RuntimeError) si la ligne n'existe pas.
            return False
        return True

    def _key(self, doc_type: DocType) -> sa.ColumnElement[bool]:
        return sa.and_(
            document_counter.c.shop_id == self._shop_id.value,
            document_counter.c.doc_type == doc_type.value,
        )
