"""Port `DocumentNumberAllocator` : numéros définitifs continus et sans trou (RG-T05, TR-10).

Contrat (vérifié par `tests/contracts`, sur chaque adaptateur) :

- une séquence **par boutique et par type** de document, qui commence à 1 ;
- le numéro est attribué **dans la transaction** de l'unité de travail : un rollback ne le
  consomme pas, le numéro suivant le réattribue (aucun trou) ;
- deux transactions concurrentes ne reçoivent jamais le même numéro : la seconde à valider
  échoue (`VersionConflict`, à rejouer) plutôt que de créer un doublon.
"""

from abc import ABC, abstractmethod

from app.domain.shared.doc_number import DocNumber, DocType


class DocumentNumberAllocator(ABC):
    """Distributeur de numéros, lié à la boutique et à la transaction de son `UnitOfWork`."""

    @abstractmethod
    def next(self, doc_type: DocType) -> DocNumber:
        """Numéro suivant du type `doc_type` pour la boutique de l'unité de travail."""
