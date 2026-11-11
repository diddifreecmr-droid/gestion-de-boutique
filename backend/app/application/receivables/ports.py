"""Port `ReceivableRepository` (T17), lié à la boutique (gabarit `ShopRecordRepository`).

- Unicité `receivable_sale` : une seule créance par vente (CDC § 20.5) ; clé nulle pour une
  créance ancienne. Les numéros de versement `R-…` sont uniques par boutique
  (`installment_number`, contrainte de la table enfant).
- `responsible` restreint **la requête** aux créances dont l'utilisateur est le vendeur
  responsable (portée « Siens », Q-21).
- Ordre des listes : date d'ouverture puis identifiant (la plus ancienne d'abord, UC-CRE-03).
"""

from abc import abstractmethod
from collections.abc import Sequence
from datetime import date

from app.application.ports.aggregate import UniqueKey
from app.application.shops.ports import ShopRecordRepository
from app.domain.receivables.ids import InstallmentId, ReceivableId, ReminderId
from app.domain.receivables.receivable import Receivable
from app.domain.sales.ids import CustomerId
from app.domain.shared.ids import UserId

RECEIVABLE_SALE = "receivable_sale"
INSTALLMENT_NUMBER = "installment_number"


def oldest_first(receivable: Receivable) -> tuple[date, object]:
    return (receivable.opened_on, receivable.id.value)


class ReceivableRepository(ShopRecordRepository[ReceivableId, Receivable]):
    def unique_keys(self) -> Sequence[UniqueKey[Receivable]]:
        return (
            UniqueKey(
                RECEIVABLE_SALE, lambda r: None if r.sale_id is None else str(r.sale_id.value)
            ),
        )

    @abstractmethod
    def list_all(self, *, responsible: UserId | None = None) -> list[Receivable]:
        """Créances de la boutique (toutes statuts), la plus ancienne d'abord."""

    @abstractmethod
    def for_customer(
        self, customer_id: CustomerId, *, responsible: UserId | None = None
    ) -> list[Receivable]:
        """Créances du client, la plus ancienne d'abord."""

    @abstractmethod
    def find_by_installment(self, installment_id: InstallmentId) -> Receivable | None:
        """Créance portant ce versement."""

    @abstractmethod
    def find_by_reminder(self, reminder_id: ReminderId) -> Receivable | None:
        """Créance portant ce rappel."""

    @abstractmethod
    def with_due_reminders(self, today: date) -> list[Receivable]:
        """Créances non annulées ayant un rappel non fait, daté au plus `today`, pas encore
        alerté pour sa date (TR-19)."""
