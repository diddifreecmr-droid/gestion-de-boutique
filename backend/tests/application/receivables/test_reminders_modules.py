"""Rappels et module `receivables` éteint (specs § 15.1) : la tâche planifiée ne fait rien et
ne consomme aucun rappel ; réactivé, le rappel dû alerte comme d'habitude. Une vente ou un
versement par le cas d'utilisation sont refusés (`MODULE_DISABLED`)."""

from datetime import date

import pytest

from app.application.receivables.use_cases.record_installment import InstallmentCommand
from app.application.shops.ports import ShopRepository
from app.domain.alerts.alert import AlertType
from app.domain.audit.values import Performer
from app.domain.profiles.modules import AVAILABLE_MODULES, Module
from app.domain.profiles.motos import MOTOS
from app.domain.shared.ids import ShopId, UserId
from app.domain.shops.errors import ModuleDisabled
from tests.application.receivables.support import ReceivablesWorld

ADMIN = Performer(UserId.new(), "admin")


def _set_modules(world: ReceivablesWorld, shop_id: ShopId, modules: frozenset[Module]) -> None:
    with world.core.shop_uow_factory(shop_id) as uow:
        shops = ShopRepository.within(uow)
        shop = shops.current()
        shop.administer(
            modules=modules, status=None, available=MOTOS.available_modules,
            performer=ADMIN, now=world.clock.now(),
        )  # fmt: skip
        shops.update(shop)
        uow.commit()


def test_due_reminders_wait_while_receivables_is_disabled() -> None:
    world = ReceivablesWorld()
    owner, _, seller, _, view = world.scn01()
    shop = world.shop_of(owner)
    world.receivables.schedule_reminder.execute(seller, view.receivable.id, date(2026, 12, 1), "")
    _set_modules(world, shop, AVAILABLE_MODULES - {Module.RECEIVABLES})
    world.at(date(2026, 12, 1), 0)
    dispatch = world.receivables_module.dispatch_reminders
    assert dispatch.execute(shop, date(2026, 12, 1)) == 0
    with pytest.raises(ModuleDisabled):
        world.receivables.record_installment.execute(
            seller,
            InstallmentCommand(receivable_id=view.receivable.id, amount=1_000,
                               mode_id=world.mode(owner)),
        )  # fmt: skip
    _set_modules(world, shop, AVAILABLE_MODULES)
    assert dispatch.execute(shop, date(2026, 12, 1)) == 1
    found = [a for a in world.alerts(owner, seller) if a.type is AlertType.RECEIVABLE_REMINDER]
    assert len(found) == 1
