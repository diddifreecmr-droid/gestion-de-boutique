"""Adaptateur mémoire du module Créances (T17) : créances avec versements, rappels, garants.

Même sémantique que l'adaptateur SQL (`tests/contracts/test_receivables_contract.py`) :
unicité `receivable_sale` (une créance par vente), portée « Siennes » appliquée dans la
lecture, ordre « la plus ancienne d'abord ».
"""

from datetime import date

from app.application.receivables.ports import (
    INSTALLMENT_NUMBER,
    ReceivableRepository,
    oldest_first,
)
from app.domain.receivables.ids import InstallmentId, ReceivableId, ReminderId
from app.domain.receivables.receivable import Receivable
from app.domain.receivables.values import ReceivableStatus
from app.domain.sales.ids import CustomerId
from app.domain.shared.ids import UserId
from app.infrastructure.persistence.errors import duplicate
from app.infrastructure.persistence.memory.shops import _Listing


class MemoryReceivableRepository(_Listing[ReceivableId, Receivable], ReceivableRepository):
    table = "receivables"

    def _insert(self, aggregate: Receivable) -> None:
        self._require_free_numbers(aggregate)
        super()._insert(aggregate)

    def _save(self, aggregate: Receivable, *, expected_version: int) -> None:
        self._require_free_numbers(aggregate)
        super()._save(aggregate, expected_version=expected_version)

    def _require_free_numbers(self, aggregate: Receivable) -> None:
        """`installment_number` : un numéro `R-` n'appartient qu'à un versement de la boutique
        (vu dans cette transaction ; une course entre transactions n'est vue que par le SQL)."""
        mine = {i.number for i in aggregate.installments}
        for other in self.list_all():
            if other.id != aggregate.id and mine & {i.number for i in other.installments}:
                raise duplicate("installment", INSTALLMENT_NUMBER)

    def list_all(self, *, responsible: UserId | None = None) -> list[Receivable]:
        found = self._sorted(key=oldest_first)
        return [r for r in found if responsible is None or r.responsible_seller_id == responsible]

    def for_customer(
        self, customer_id: CustomerId, *, responsible: UserId | None = None
    ) -> list[Receivable]:
        return [r for r in self.list_all(responsible=responsible) if r.customer_id == customer_id]

    def find_by_installment(self, installment_id: InstallmentId) -> Receivable | None:
        found = [r for r in self.list_all() if any(i.id == installment_id for i in r.installments)]
        return found[0] if found else None

    def find_by_reminder(self, reminder_id: ReminderId) -> Receivable | None:
        found = [r for r in self.list_all() if any(m.id == reminder_id for m in r.reminders)]
        return found[0] if found else None

    def with_due_reminders(self, today: date) -> list[Receivable]:
        return [
            r
            for r in self.list_all()
            if r.status is not ReceivableStatus.CANCELLED
            and any(m.is_due(today) for m in r.reminders)
        ]


MEMORY_RECEIVABLES_REPOSITORIES = (MemoryReceivableRepository,)
