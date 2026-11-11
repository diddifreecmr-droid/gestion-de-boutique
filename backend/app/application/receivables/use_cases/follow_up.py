"""Suivi d'une créance (`RECEIVABLE_FOLLOW_UP` : propriétaire, vendeur sur ses créances).

- `ChangeReceivable` (UC-CRE-01 « le propriétaire peut le changer », Q-21) : conditions
  convenues et pièces jointes (identifiants) ; le **vendeur responsable** ne change que par le
  propriétaire (sinon 403 `FORBIDDEN`, permission `RECEIVABLE_CREATE`, propriétaire seul).
  `PATCH` + `version` (409 si la créance a changé).
- `ScheduleReminder` / `ChangeReminder` (UC-CRE-06) : date (future acceptée), note ; fait,
  reporté. Aucun message au client (H19).
- `AddGuarantor` (UC-CRE-07) : nom, téléphone, lien, pièce d'identité.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import date
from typing import Any

from app.application.ports.clock import Clock
from app.application.ports.repository import not_found
from app.application.ports.uow import UnitOfWorkFactory
from app.application.receivables.access import (
    ReceivableView,
    require_in_scope,
    responsible_scope,
    view_of,
    visible_receivable,
)
from app.application.receivables.ports import ReceivableRepository
from app.application.receivables.retry import with_receivable_retry
from app.application.receivables.use_cases.record_legacy import require_seller
from app.application.security.actor import Actor
from app.application.security.errors import PermissionDenied
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.security.roles import Role
from app.application.shops.context import actor_shop, performer_of, require_version
from app.domain.audit.values import Performer
from app.domain.receivables.follow_up import Guarantor, Reminder, ReminderStatus
from app.domain.receivables.ids import GuarantorId, ReceivableId, ReminderId
from app.domain.receivables.receivable import Receivable
from app.domain.shared.ids import UserId

PATCHABLE = frozenset({"responsible_seller_id", "terms", "attachment_ids"})
FOLLOW_UP = Permission.RECEIVABLE_FOLLOW_UP


@dataclass(frozen=True, slots=True, kw_only=True)
class ReminderChange:
    reminder_id: ReminderId
    status: ReminderStatus | None = None
    remind_on: date | None = None
    note: str | None = None


class _FollowUp:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock

    def _apply(
        self,
        actor: Actor,
        load: Callable[[ReceivableRepository, UserId | None], Receivable],
        change: Callable[[Receivable, Performer], None],
    ) -> ReceivableView:
        responsible = responsible_scope(self._policy, actor, FOLLOW_UP)

        def attempt() -> ReceivableView:
            with self._uow_factory(actor_shop(actor)) as uow:
                receivables = ReceivableRepository.within(uow)
                receivable = load(receivables, responsible)
                change(receivable, performer_of(actor))
                receivables.update(receivable)
                view = view_of(uow, actor, receivable, self._clock.today())
                uow.commit()
            return view

        return with_receivable_retry(attempt)

    @staticmethod
    def by_id(receivable_id: ReceivableId) -> Callable[..., Receivable]:
        def load(receivables: ReceivableRepository, responsible: UserId | None) -> Receivable:
            receivable = receivables.get(receivable_id)
            require_in_scope(receivable, responsible)
            return receivable

        return load


class ChangeReceivable(_FollowUp):
    def execute(
        self, actor: Actor, receivable_id: ReceivableId, version: int, patch: Mapping[str, Any]
    ) -> ReceivableView:
        unknown = set(patch) - PATCHABLE
        if unknown:
            msg = f"Champs de créance inconnus : {sorted(unknown)}"
            raise ValueError(msg)
        responsible = responsible_scope(self._policy, actor, FOLLOW_UP)
        if "responsible_seller_id" in patch and actor.role is not Role.OWNER:
            raise PermissionDenied(actor, Permission.RECEIVABLE_CREATE)
        now = self._clock.now()
        with self._uow_factory(actor_shop(actor)) as uow:
            receivable = visible_receivable(uow, receivable_id, responsible)
            require_version(receivable.version, version)
            if "responsible_seller_id" in patch:
                require_seller(uow, patch["responsible_seller_id"])
            receivables = ReceivableRepository.within(uow)
            new_terms = replace(receivable.tracked_terms, **dict(patch))
            if receivable.change(new_terms, performer=performer_of(actor), now=now):
                receivables.update(receivable)
            view = view_of(uow, actor, receivable, self._clock.today())
            uow.commit()
        return view


class ScheduleReminder(_FollowUp):
    def execute(
        self,
        actor: Actor,
        receivable_id: ReceivableId,
        remind_on: date,
        note: str | None,
        reminder_id: ReminderId | None = None,
    ) -> ReceivableView:
        def change(receivable: Receivable, performer: Performer) -> None:
            reminder = Reminder(
                id=reminder_id or ReminderId.new(),
                remind_on=remind_on,
                note=note,
                created_by=actor.user_id,
                created_at=self._clock.now(),
            )
            receivable.add_reminder(reminder, performer=performer)

        return self._apply(actor, self.by_id(receivable_id), change)


class ChangeReminder(_FollowUp):
    def execute(self, actor: Actor, command: ReminderChange) -> ReceivableView:
        def load(receivables: ReceivableRepository, responsible: UserId | None) -> Receivable:
            receivable = receivables.find_by_reminder(command.reminder_id)
            if receivable is None:
                raise not_found(command.reminder_id)
            require_in_scope(receivable, responsible)
            return receivable

        def change(receivable: Receivable, performer: Performer) -> None:
            receivable.change_reminder(
                command.reminder_id,
                status=command.status,
                remind_on=command.remind_on,
                note=command.note,
                performer=performer,
                now=self._clock.now(),
            )

        return self._apply(actor, load, change)


class AddGuarantor(_FollowUp):
    def execute(
        self, actor: Actor, receivable_id: ReceivableId, details: Mapping[str, Any]
    ) -> ReceivableView:
        def change(receivable: Receivable, performer: Performer) -> None:
            guarantor = Guarantor(
                id=details.get("id") or GuarantorId.new(),
                added_by=actor.user_id,
                added_at=self._clock.now(),
                **{k: v for k, v in details.items() if k != "id"},
            )
            receivable.add_guarantor(guarantor, performer=performer)

        return self._apply(actor, self.by_id(receivable_id), change)
