"""UC-CRE-05 — Compte d'un client : relevé chronologique (REC-06 ; M22).

Ventes à crédit, acomptes, créances anciennes, versements, pertes et annulations du client,
avec le **reste à payer après chaque opération** (`statement_lines.py`). Les ventes au comptant
ne changent pas le dû et n'y figurent pas. Le vendeur ne lit que le compte de ses clients
(sinon 404) et, dedans, que ses créances (portée « Siennes »).
"""

from dataclasses import dataclass

from app.application.ports.uow import UnitOfWorkFactory
from app.application.receivables.access import responsible_scope
from app.application.receivables.ports import ReceivableRepository
from app.application.receivables.statement_lines import StatementLine, statement_lines
from app.application.sales.resolver import require_visible
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop
from app.domain.sales.customer import Customer
from app.domain.sales.ids import CustomerId
from app.domain.shared.money import Money


@dataclass(frozen=True, slots=True)
class Statement:
    customer: Customer
    lines: list[StatementLine]
    total_due: Money


class CustomerStatement:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy) -> None:
        self._uow_factory = uow_factory
        self._policy = policy

    def execute(self, actor: Actor, customer_id: CustomerId) -> Statement:
        self._policy.require(actor, Permission.CUSTOMER_READ)
        responsible = responsible_scope(self._policy, actor, Permission.RECEIVABLE_READ)
        with self._uow_factory(actor_shop(actor)) as uow:
            customer = require_visible(uow, actor, customer_id)
            found = ReceivableRepository.within(uow).for_customer(
                customer_id, responsible=responsible
            )
        due = Money.total(r.remaining for r in found if r.counts_as_due)
        return Statement(customer, statement_lines(found), due)
