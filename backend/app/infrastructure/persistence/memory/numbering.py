"""Numérotation mémoire : compteur par (boutique, type), tenu dans la transaction."""

from app.application.ports.numbering import DocumentNumberAllocator
from app.domain.shared.doc_number import DocNumber, DocType
from app.infrastructure.persistence.memory.transaction import MemoryTransaction


class MemoryDocumentNumberAllocator(DocumentNumberAllocator):
    """Le compteur validé n'avance qu'au commit ; un rollback ne consomme aucun numéro."""

    def __init__(self, transaction: MemoryTransaction) -> None:
        self._transaction = transaction

    def next(self, doc_type: DocType) -> DocNumber:
        if not isinstance(doc_type, DocType):
            msg = f"doc_type doit être un DocType, reçu {doc_type!r}"
            raise TypeError(msg)
        return DocNumber(doc_type, self._transaction.next_sequence(doc_type))
