"""UC-DEP-03 — Détail d'une dépense (`GET /expenses/{id}`) : comptable, propriétaire.

Une dépense d'une autre boutique est introuvable (404, aucune fuite d'existence, specs § 8.3).
"""

from app.application.expenses.ports import ExpenseRepository
from app.application.expenses.views import ExpenseView, tag_index, view_of
from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWorkFactory
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop
from app.domain.expenses.ids import ExpenseId


class GetExpense:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock

    def execute(self, actor: Actor, expense_id: ExpenseId) -> ExpenseView:
        self._policy.require(actor, Permission.EXPENSE_READ)
        with self._uow_factory(actor_shop(actor)) as uow:
            expense = ExpenseRepository.within(uow).get(expense_id)
            return view_of(actor, expense, tag_index(uow), self._clock.now())
