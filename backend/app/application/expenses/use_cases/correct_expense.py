"""UC-DEP-04 — Corriger une dépense (`PATCH` + `version`, specs § 6.1 ; recette EXP-06).

Auteur (comptable) : ses dépenses, jusqu'à minuit (Douala) le jour de la saisie ; propriétaire :
toujours (`require_correction`). Les champs absents du `patch` gardent leur valeur ; ceux
présents sont revérifiés comme à la saisie (date RG-T09, « Autre » + description, catégorie,
mode et lieu actifs s'ils changent). Le numéro, l'auteur et la capture ne changent jamais.
Chaque champ modifié est journalisé avant/après (UC-JRN-02). Version périmée → 409.
"""

from collections.abc import Mapping
from dataclasses import fields, replace
from typing import Any

from app.application.expenses.ports import ExpenseRepository
from app.application.expenses.references import DetailsResolver, ExpenseInput
from app.application.expenses.views import ExpenseView, require_correction, tag_index, view_of
from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWorkFactory
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.security.roles import Role
from app.application.shops.context import actor_shop, performer_of, require_version
from app.domain.expenses.details import ExpenseDetails
from app.domain.expenses.ids import ExpenseId, TagId
from app.domain.expenses.tag import Tag

PATCHABLE = frozenset(f.name for f in fields(ExpenseInput))


def input_of(details: ExpenseDetails, tags: Mapping[TagId, Tag]) -> ExpenseInput:
    """Saisie équivalente aux détails enregistrés (point de départ d'un `patch`)."""
    return ExpenseInput(
        amount=details.amount,
        category_id=details.category_id,
        spent_on=details.spent_on,
        payment_mode_id=details.payment_mode_id,
        tag_names=tuple(tags[tag].name for tag in details.tag_ids),
        description=details.description,
        location_id=details.location_id,
        beneficiary=details.beneficiary,
        attachment_id=details.attachment_id,
    )


class CorrectExpense:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock

    def execute(
        self, actor: Actor, expense_id: ExpenseId, patch: Mapping[str, Any], version: int
    ) -> ExpenseView:
        unknown = set(patch) - PATCHABLE
        if unknown:
            msg = f"Champs non modifiables : {sorted(unknown)}"
            raise ValueError(msg)
        self._policy.require(actor, Permission.EXPENSE_CORRECT)  # avant toute lecture
        now = self._clock.now()
        with self._uow_factory(actor_shop(actor)) as uow:
            expenses = ExpenseRepository.within(uow)
            expense = expenses.get(expense_id)
            require_correction(self._policy, actor, expense, now)
            require_version(expense.version, version)
            performer = performer_of(actor)
            data = replace(input_of(expense.details, tag_index(uow)), **patch)
            details = DetailsResolver(uow, performer, now).resolve(
                data,
                today=self._clock.today(),
                is_owner=actor.role is Role.OWNER,
                previous=expense.details,
            )
            changed = expense.correct(details, performer=performer, now=now)
            if changed:
                expenses.update(expense)
            view = view_of(actor, expense, tag_index(uow), now)
            if changed:
                uow.commit()
        return view
