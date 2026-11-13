"""`AlertDispatcher` dans la transaction : « une seule fois » (LOW-01, ALR-04), résolution."""

from typing import Any

import pytest

from app.application.alerts.dispatcher import AlertDispatcher, AlertNotice
from app.application.alerts.ports import AlertRepository
from app.application.ports.pagination import PageRequest
from app.application.ports.uow import UnitOfWork
from app.domain.alerts.alert import Alert, AlertType
from app.domain.profiles.modules import ALL_MODULES
from app.domain.shared.errors import Duplicate
from app.domain.shared.ids import ShopId, UserId
from app.infrastructure.persistence.memory.clock import FixedClock
from tests.contracts.alerting import (
    ACCOUNTANT,
    ARTICLE,
    OWNER,
    StockChanged,
    low_stock_rule,
    stock_event,
)
from tests.contracts.backends import ContractBackend
from tests.contracts.helpers import run_in_uow, widgets
from tests.contracts.widget import NOW, WidgetCreated


def dispatcher() -> AlertDispatcher:
    handler = AlertDispatcher(FixedClock(NOW), modules=lambda uow: ALL_MODULES)
    handler.register(StockChanged, low_stock_rule)
    return handler


def emit(backend: ContractBackend, shop: ShopId, level: int, handler: AlertDispatcher) -> None:
    widget = stock_event(shop, level)
    run_in_uow(backend, shop, lambda uow: widgets(uow).add(widget), [handler])


def mine(backend: ContractBackend, shop: ShopId, user: UserId) -> list[Alert]:
    with backend.uow(shop) as uow:
        return list(AlertRepository.within(uow).for_recipient(user, PageRequest()).items)


def test_low_stock_alerts_owner_and_accountant_only_once(
    backend: ContractBackend, shop_a: ShopId
) -> None:
    handler = dispatcher()
    emit(backend, shop_a, 4, handler)  # 6 → 4 : une alerte à O et C (O dédoublonné)
    emit(backend, shop_a, 3, handler)  # → 3 : aucune nouvelle alerte
    assert [a.message for a in mine(backend, shop_a, OWNER)] == ["Stock bas : HJ125 (4)"]
    assert len(mine(backend, shop_a, ACCOUNTANT)) == 1
    emit(backend, shop_a, 7, handler)  # achat : stock remonté, alertes résolues
    assert [a.active for a in mine(backend, shop_a, OWNER)] == [False]
    emit(backend, shop_a, 4, handler)  # nouvelle baisse : nouvelle alerte
    assert [a.active for a in mine(backend, shop_a, OWNER)] == [True, False]


def test_events_without_rule_are_ignored(backend: ContractBackend, shop_a: ShopId) -> None:
    handler = dispatcher()
    widget = stock_event(shop_a, 9)
    widget.events.record(
        WidgetCreated(shop_id=shop_a, occurred_at=NOW, widget_id=widget.id, label="x")
    )
    run_in_uow(backend, shop_a, lambda uow: widgets(uow).add(widget), [handler])
    assert mine(backend, shop_a, OWNER) == []


def test_concurrent_creation_counts_as_already_alerted(
    backend: ContractBackend, shop_a: ShopId, monkeypatch: pytest.MonkeyPatch
) -> None:
    handler = dispatcher()
    emit(backend, shop_a, 2, handler)  # une autre transaction a créé l'alerte et validé
    with backend.uow(shop_a) as racing:
        repository = AlertRepository.within(racing)  # même instance pour le dispatcher
        monkeypatch.setattr(repository, "find_active", lambda *_: None)  # lu avant la course
        handler.handle(StockChanged(shop_id=shop_a, occurred_at=NOW, level=1), racing)
        racing.commit()
    assert len(mine(backend, shop_a, OWNER)) == 1


def test_other_duplicates_are_not_swallowed(
    backend: ContractBackend, shop_a: ShopId, monkeypatch: pytest.MonkeyPatch
) -> None:
    taken = Alert.raise_for(
        shop_id=shop_a,
        recipient_id=OWNER,
        type=AlertType.PRICE_REQUEST,
        entity=ARTICLE,
        message="Demande",
        now=NOW,
    )
    real = Alert.raise_for

    def same_id(**kwargs: Any) -> Alert:
        alert = real(**kwargs)
        alert.id = taken.id  # identifiant déjà pris : violation de clé primaire
        return alert

    run_in_uow(backend, shop_a, lambda uow: AlertRepository.within(uow).add(taken))
    monkeypatch.setattr(Alert, "raise_for", same_id)
    handler = AlertDispatcher(FixedClock(NOW), modules=lambda uow: ALL_MODULES)

    def rule(event: StockChanged, uow: UnitOfWork) -> list[AlertNotice]:
        return [AlertNotice(recipients=(OWNER,), type=taken.type, entity=ARTICLE, message="m")]

    handler.register(StockChanged, rule)
    with pytest.raises(Duplicate) as caught:
        emit(backend, shop_a, 1, handler)
    assert caught.value.details["constraint"] == "id"


def test_register_refuses_non_event_types() -> None:
    with pytest.raises(TypeError, match="DomainEvent"):
        dispatcher().register(int, low_stock_rule)  # type: ignore[type-var, arg-type]
