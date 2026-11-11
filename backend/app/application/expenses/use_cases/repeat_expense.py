"""UC-DEP-05 — « Refaire cette dépense » (`GET /expenses/{id}/repeat` ; recette EXP-07).

Renvoie un **brouillon** pré-rempli — montant, catégorie, tags, bénéficiaire — daté du jour
(Douala). Rien n'est enregistré : la nouvelle dépense passe ensuite par `RecordExpense` et
reçoit son propre numéro. Utile pour le loyer ou un salaire mensuel. Droit : saisir une
dépense (`EXPENSE_CREATE`) ; une dépense annulée peut aussi servir de modèle.
"""

from dataclasses import dataclass

from app.application.expenses.ports import ExpenseRepository
from app.application.expenses.views import tag_index
from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWorkFactory
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop
from app.domain.expenses.details import ExpenseDraft
from app.domain.expenses.ids import ExpenseId
from app.domain.expenses.tag import Tag


@dataclass(frozen=True, slots=True)
class DraftView:
    draft: ExpenseDraft
    tags: tuple[Tag, ...]


class RepeatExpense:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock

    def execute(self, actor: Actor, expense_id: ExpenseId) -> DraftView:
        self._policy.require(actor, Permission.EXPENSE_CREATE)
        with self._uow_factory(actor_shop(actor)) as uow:
            expense = ExpenseRepository.within(uow).get(expense_id)
            tags = tag_index(uow)
        draft = expense.repeat(self._clock.today())
        return DraftView(draft, tuple(tags[tag] for tag in draft.tag_ids))
