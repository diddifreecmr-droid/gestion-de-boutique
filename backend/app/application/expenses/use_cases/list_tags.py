"""UC-DEP-02 — Lister les tags (`GET /tags`) pour le champ de saisie (comptable, propriétaire).

Seuls les tags **non fusionnés** sont proposés, par nom (sans casse). `search` filtre sur une
partie du nom, sans tenir compte de la casse (même normalisation que l'unicité, `tag_key`).
"""

from app.application.expenses.ports import TagRepository
from app.application.ports.uow import UnitOfWorkFactory
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop
from app.domain.expenses.tag import Tag, tag_key


class ListTags:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy) -> None:
        self._uow_factory = uow_factory
        self._policy = policy

    def execute(self, actor: Actor, search: str | None = None) -> list[Tag]:
        self._policy.require(actor, Permission.TAG_READ)
        with self._uow_factory(actor_shop(actor)) as uow:
            tags = TagRepository.within(uow).list_all()
        needle = None if search is None else tag_key(search)
        return [tag for tag in tags if not tag.is_merged and (not needle or needle in tag.name_key)]
