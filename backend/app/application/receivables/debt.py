"""Dû actuel d'un client (« Total dû », CDC § 20.4) servi aux Ventes (port `CustomerDebt`).

Somme des restes des créances **En cours** du client (§ 10.1) : versements déduits ; Soldée,
Annulée et En perte n'y comptent pas. Sert au plafond de crédit (UC-VEN-02, ERR-CRD-02/03).
"""

from app.application.ports.uow import UnitOfWork
from app.application.receivables.ports import ReceivableRepository
from app.application.sales.checks import CustomerDebt
from app.domain.sales.ids import CustomerId
from app.domain.shared.money import Money


class ReceivableCustomerDebt(CustomerDebt):
    def due(self, uow: UnitOfWork, customer_id: CustomerId) -> Money:
        receivables = ReceivableRepository.within(uow).for_customer(customer_id)
        return Money.total(r.remaining for r in receivables if r.counts_as_due)
