"""Contrat `AlertRepository` : par destinataire, unicité « active + clé », isolation."""

import pytest

from app.application.alerts.ports import ALERT_ACTIVE_DEDUP, AlertRepository
from app.application.ports.pagination import PageRequest
from app.application.ports.uow import UnitOfWork
from app.domain.alerts.alert import Alert
from app.domain.shared.errors import Duplicate, NotFound
from app.domain.shared.ids import ShopId
from tests.contracts.alerting import ACCOUNTANT, OWNER, alert_for
from tests.contracts.backends import ContractBackend
from tests.contracts.helpers import run_in_uow
from tests.contracts.widget import NOW


def add(backend: ContractBackend, shop: ShopId, *alerts: Alert) -> None:
    def action(uow: UnitOfWork) -> None:
        repository = AlertRepository.within(uow)
        for alert in alerts:
            repository.add(alert)

    run_in_uow(backend, shop, action)


def test_round_trip_and_unread_count(backend: ContractBackend, shop_a: ShopId) -> None:
    mine, other = alert_for(shop_a), alert_for(shop_a, ACCOUNTANT)
    add(backend, shop_a, mine, other)
    with backend.uow(shop_a) as uow:
        alerts = AlertRepository.within(uow)
        stored = alerts.get(mine.id)
        assert (stored.message, stored.created_at, stored.read, stored.active) == (
            mine.message,
            NOW,
            False,
            True,
        )
        assert alerts.unread_count(OWNER) == 1
        stored.mark_read()
        alerts.update(stored)
        uow.commit()
    with backend.uow(shop_a) as uow:
        alerts = AlertRepository.within(uow)
        assert alerts.unread_count(OWNER) == 0
        assert alerts.unread_count(ACCOUNTANT) == 1
        assert alerts.for_recipient(OWNER, PageRequest(), unread_only=True).items == []


def test_listing_is_per_recipient_newest_first_and_paginated(
    backend: ContractBackend, shop_a: ShopId
) -> None:
    created = [alert_for(shop_a, key=None, minute=i) for i in range(3)]
    add(backend, shop_a, *created, alert_for(shop_a, ACCOUNTANT, key=None))
    with backend.uow(shop_a) as uow:
        alerts = AlertRepository.within(uow)
        first = alerts.for_recipient(OWNER, PageRequest(2))
        assert first.next_cursor is not None
        rest = alerts.for_recipient(OWNER, PageRequest(2, first.next_cursor))
    ids = [a.id for a in [*first.items, *rest.items]]
    assert ids == [a.id for a in reversed(created)]
    assert rest.next_cursor is None


def test_second_active_alert_with_same_key_is_a_duplicate(
    backend: ContractBackend, shop_a: ShopId, shop_b: ShopId
) -> None:
    add(backend, shop_a, alert_for(shop_a))
    with pytest.raises(Duplicate) as caught:
        add(backend, shop_a, alert_for(shop_a))
    assert caught.value.details["constraint"] == ALERT_ACTIVE_DEDUP
    add(backend, shop_a, alert_for(shop_a, ACCOUNTANT))  # autre destinataire : permis
    add(backend, shop_b, alert_for(shop_b))  # autre boutique : permis
    add(backend, shop_a, alert_for(shop_a, key=None), alert_for(shop_a, key=None))


def test_resolving_frees_the_key(backend: ContractBackend, shop_a: ShopId) -> None:
    first = alert_for(shop_a)
    add(backend, shop_a, first)
    with backend.uow(shop_a) as uow:
        alerts = AlertRepository.within(uow)
        (active,) = alerts.active_with_key("k")
        assert alerts.find_active(OWNER, "k") is not None
        active.resolve(NOW)
        alerts.update(active)
        uow.commit()
    add(backend, shop_a, alert_for(shop_a))
    with backend.uow(shop_a) as uow:
        alerts = AlertRepository.within(uow)
        assert alerts.find_active(OWNER, "k") is not None
        assert alerts.get(first.id).active is False
        assert alerts.find_active(ACCOUNTANT, "k") is None


def test_shop_b_never_sees_alerts_of_shop_a(
    backend: ContractBackend, shop_a: ShopId, shop_b: ShopId
) -> None:
    alert = alert_for(shop_a)
    add(backend, shop_a, alert)
    with backend.uow(shop_b) as uow:
        alerts = AlertRepository.within(uow)
        assert alerts.for_recipient(OWNER, PageRequest()).items == []
        assert alerts.unread_count(OWNER) == 0
        assert alerts.active_with_key("k") == []
        with pytest.raises(NotFound):
            alerts.get(alert.id)
