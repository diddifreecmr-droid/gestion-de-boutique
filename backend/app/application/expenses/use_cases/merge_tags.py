"""UC-DEP-02 — Fusionner deux tags (`POST /tags/merge` ; propriétaire seul, recette EXP-04).

« groupe » fusionné dans « groupe électrogène » :

- le tag source garde son nom et pointe vers la cible (`merged_into`) ; retaper « groupe »
  à la saisie donne la cible ;
- les tags déjà fusionnés dans la source pointent désormais vers la cible (un seul saut) ;
- **réécriture** documentée : toutes les dépenses (annulées comprises) qui portaient la source
  portent la cible, dans la même transaction (version incrémentée ; le journal garde une
  entrée pour la fusion, pas une par dépense). Les filtres et totaux par tag n'ont donc
  jamais à suivre de chaîne de fusion.
"""

from dataclasses import dataclass

from app.application.expenses.ports import ExpenseRepository, TagRepository
from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWorkFactory
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop, performer_of
from app.domain.expenses.ids import TagId
from app.domain.expenses.tag import Tag


@dataclass(frozen=True, slots=True)
class MergeResult:
    target: Tag
    retagged_expenses: int


class MergeTags:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock

    def execute(self, actor: Actor, source_id: TagId, target_id: TagId) -> MergeResult:
        self._policy.require(actor, Permission.TAG_MERGE)
        with self._uow_factory(actor_shop(actor)) as uow:
            tags = TagRepository.within(uow)
            source, target = tags.get(source_id), tags.get(target_id)
            source.merge_into(target, performer=performer_of(actor), now=self._clock.now())
            tags.update(source)
            for earlier in tags.list_all():
                if earlier.merged_into == source.id:
                    earlier.repoint(target.id)
                    tags.update(earlier)
            expenses = ExpenseRepository.within(uow)
            retagged = 0
            for expense in expenses.list_with_tag(source.id):
                if expense.retag(source.id, target.id):
                    expenses.update(expense)
                    retagged += 1
            uow.commit()
        return MergeResult(target, retagged)
