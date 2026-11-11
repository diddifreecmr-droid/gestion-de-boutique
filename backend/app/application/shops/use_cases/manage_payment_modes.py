"""Gérer les modes de paiement (UC-SOC-06, RG-T19 ; recette SET-01, SET-03).

- Lister : tout membre (`HOME_READ`) — le vendeur et le comptable choisissent un mode à la
  saisie — voit les modes **actifs** ; le propriétaire (`SETTINGS_MANAGE`) les voit tous.
- Ajouter (« Wave »…), renommer, demander ou non la référence, désactiver, réordonner :
  propriétaire seul ; chaque changement est journalisé (action « Régler »). Un nouveau mode est
  proposé à la saisie suivante (aucun cache côté serveur).
- Création idempotente : un `mode_id` déjà connu renvoie le mode existant (`created=False`).
"""

from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWorkFactory
from app.application.security.access import Access
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.security.role_matrix import access_for
from app.application.shops.context import actor_shop, performer_of, require_version
from app.application.shops.ports import PaymentModeRepository
from app.domain.shops.ids import PaymentModeId
from app.domain.shops.payment_mode import PaymentMode, PaymentModeDetails


class ManagePaymentModes:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock

    def list(self, actor: Actor) -> list[PaymentMode]:
        self._policy.require(actor, Permission.HOME_READ)
        with self._uow_factory(actor_shop(actor)) as uow:
            modes = PaymentModeRepository.within(uow).list_all()
        if self._manages(actor):
            return modes
        return [mode for mode in modes if mode.details.active]

    def create(
        self, actor: Actor, details: PaymentModeDetails, mode_id: PaymentModeId | None = None
    ) -> tuple[PaymentMode, bool]:
        self._policy.require(actor, Permission.SETTINGS_MANAGE)
        with self._uow_factory(actor_shop(actor)) as uow:
            modes = PaymentModeRepository.within(uow)
            existing = None if mode_id is None else modes.find(mode_id)
            if existing is not None:
                return existing, False
            mode = PaymentMode.create(
                uow.shop_id,
                details,
                performer=performer_of(actor),
                now=self._clock.now(),
                mode_id=mode_id,
            )
            modes.add(mode)
            uow.commit()
        return mode, True

    def update(
        self, actor: Actor, mode_id: PaymentModeId, patch: Mapping[str, Any], version: int
    ) -> PaymentMode:
        self._policy.require(actor, Permission.SETTINGS_MANAGE)
        with self._uow_factory(actor_shop(actor)) as uow:
            modes = PaymentModeRepository.within(uow)
            mode = modes.get(mode_id)
            require_version(mode.version, version)
            details = replace(mode.details, **patch)
            if mode.change(details, performer=performer_of(actor), now=self._clock.now()):
                modes.update(mode)
                uow.commit()
        return mode

    @staticmethod
    def _manages(actor: Actor) -> bool:
        """Le propriétaire voit aussi les modes désactivés ; l'admin délégué ne gère rien."""
        if actor.role is None:
            return False
        return access_for(actor.role, Permission.SETTINGS_MANAGE) is Access.ALL
