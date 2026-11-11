"""UC-DEP-01 — Enregistrer une dépense (comptable, propriétaire ; recette EXP-01).

Montant, catégorie, puis valider : date du jour, mode « Espèces » par défaut. Le numéro
`D-000001` est attribué dans la transaction (RG-T05, TR-10 : continu, sans trou). Les tags
nouveaux sont créés à la volée (UC-DEP-02).

Idempotence (specs § 6.1, TR-11) : un `expense_id` client déjà enregistré renvoie la dépense
existante (`created=False`) sans rien réécrire ni consommer de numéro. `captured_at` (heure de
l'appareil, `X-Captured-At`) et `device_id` sont gardés pour la saisie hors ligne (RG-T04).
"""

from dataclasses import dataclass
from datetime import datetime

from app.application.expenses.ports import ExpenseRepository
from app.application.expenses.references import (
    DetailsResolver,
    ExpenseInput,
    checked_capture_time,
)
from app.application.expenses.views import ExpenseView, tag_index, view_of
from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWorkFactory
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.security.roles import Role
from app.application.shops.context import actor_shop, performer_of
from app.domain.expenses.details import Capture
from app.domain.expenses.expense import Expense
from app.domain.expenses.ids import ExpenseId
from app.domain.shared.doc_number import DocType


@dataclass(frozen=True, slots=True, kw_only=True)
class RecordExpenseCommand:
    data: ExpenseInput
    expense_id: ExpenseId | None = None
    captured_at: datetime | None = None


class RecordExpense:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock

    def execute(self, actor: Actor, command: RecordExpenseCommand) -> tuple[ExpenseView, bool]:
        self._policy.require(actor, Permission.EXPENSE_CREATE)
        now = self._clock.now()
        with self._uow_factory(actor_shop(actor)) as uow:
            expenses = ExpenseRepository.within(uow)
            if command.expense_id is not None:
                existing = expenses.find(command.expense_id)
                if existing is not None:
                    return view_of(actor, existing, tag_index(uow), now), False
            performer = performer_of(actor)
            details = DetailsResolver(uow, performer, now).resolve(
                command.data, today=self._clock.today(), is_owner=actor.role is Role.OWNER
            )
            capture = Capture(
                created_by=actor.user_id,
                device_id=actor.device_id,
                captured_at=checked_capture_time(command.captured_at, now),
                received_at=now,
            )
            expense = Expense.record(
                uow.shop_id,
                uow.numbering.next(DocType.EXPENSE),
                details,
                capture,
                performer=performer,
                expense_id=command.expense_id,
            )
            expenses.add(expense)
            view = view_of(actor, expense, tag_index(uow), now)
            uow.commit()
        return view, True
