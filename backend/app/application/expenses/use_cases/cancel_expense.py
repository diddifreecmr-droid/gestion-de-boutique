"""UC-DEP-04 — Annuler une dépense (`POST /expenses/{id}/cancel {reason}` ; recette EXP-06).

Mêmes droits et même délai que la correction (`require_correction`). Motif obligatoire
(`REASON_REQUIRED`, 400). La dépense reste visible avec la date, l'auteur et le motif ; elle
sort de tous les totaux (RG-T03, H11). L'annulation est journalisée « sensible ». Annuler une
dépense déjà annulée → `INVALID_STATE_TRANSITION` (422).
"""

from app.application.expenses.ports import ExpenseRepository
from app.application.expenses.views import ExpenseView, require_correction, tag_index, view_of
from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWorkFactory
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop, performer_of
from app.domain.expenses.ids import ExpenseId


class CancelExpense:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock

    def execute(self, actor: Actor, expense_id: ExpenseId, reason: str) -> ExpenseView:
        self._policy.require(actor, Permission.EXPENSE_CORRECT)  # avant toute lecture
        now = self._clock.now()
        with self._uow_factory(actor_shop(actor)) as uow:
            expenses = ExpenseRepository.within(uow)
            expense = expenses.get(expense_id)
            require_correction(self._policy, actor, expense, now)
            expense.cancel(reason, performer=performer_of(actor), now=now)
            expenses.update(expense)
            view = view_of(actor, expense, tag_index(uow), now)
            uow.commit()
        return view
