"""Délégation de l'administrateur plateforme : accorder, retirer, consulter (specs § 8.3, § 15.1).

Le **propriétaire** seul (`MEMBER_MANAGE`, CDC § 4.1 « sans l'accord du propriétaire »)
accorde à l'administrateur 24 h de consultation de sa boutique (`GrantAdminAccess`), la retire
avant terme (`RevokeAdminAccess`) ou voit si elle court (`current`). Accorder alors qu'une
délégation court la remplace (nouvelles 24 h). Tout est journalisé, signalé sensible. Retirer
sans délégation active → `INVALID_STATE_TRANSITION` (422).
"""

from datetime import timedelta

from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWorkFactory
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop, performer_of
from app.application.shops.ports import AdminGrantRepository
from app.domain.shared.errors import InvalidStateTransition
from app.domain.shops.admin_grant import DEFAULT_GRANT_DURATION, AdminAccessGrant


class GrantAdminAccess:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        policy: Policy,
        clock: Clock,
        duration: timedelta = DEFAULT_GRANT_DURATION,
    ) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock
        self._duration = duration

    def execute(self, actor: Actor) -> AdminAccessGrant:
        self._policy.require(actor, Permission.MEMBER_MANAGE)
        now, performer = self._clock.now(), performer_of(actor)
        with self._uow_factory(actor_shop(actor)) as uow:
            grants = AdminGrantRepository.within(uow)
            running = grants.active(now)
            if running is not None:
                running.revoke(performer=performer, now=now)
                grants.update(running)
            grant = AdminAccessGrant.grant(
                shop_id=uow.shop_id, performer=performer, now=now, duration=self._duration
            )
            grants.add(grant)
            uow.commit()
        return grant

    def current(self, actor: Actor) -> AdminAccessGrant | None:
        self._policy.require(actor, Permission.MEMBER_MANAGE)
        with self._uow_factory(actor_shop(actor)) as uow:
            return AdminGrantRepository.within(uow).active(self._clock.now())


class RevokeAdminAccess:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock

    def execute(self, actor: Actor) -> None:
        self._policy.require(actor, Permission.MEMBER_MANAGE)
        now = self._clock.now()
        with self._uow_factory(actor_shop(actor)) as uow:
            grants = AdminGrantRepository.within(uow)
            running = grants.active(now)
            if running is None:
                msg = "Aucun accès de l'administrateur n'est en cours"
                raise InvalidStateTransition(msg)
            running.revoke(performer=performer_of(actor), now=now)
            grants.update(running)
            uow.commit()
