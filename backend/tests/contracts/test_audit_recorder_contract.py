"""`AuditRecorder` dans la transaction (TR-09, D7) : l'action et sa trace, ou rien du tout."""

from datetime import timedelta

import pytest

from app.application.audit.ports import AuditLog, AuditQuery
from app.application.audit.recorder import AuditRecorder
from app.application.ports.pagination import PageRequest
from app.domain.audit.entry import AuditEntry
from app.domain.audit.events import UnauditedEvent
from app.domain.audit.values import AuditAction
from app.domain.shared.errors import NotFound
from app.domain.shared.ids import ShopId
from app.infrastructure.persistence.memory.clock import FixedClock
from tests.contracts.audited import AUTHOR, WidgetAudited, WidgetBroken, WidgetIgnored, widget_with
from tests.contracts.backends import ContractBackend
from tests.contracts.handlers import FailingHandler, HandlerFailure
from tests.contracts.helpers import run_in_uow, widgets
from tests.contracts.widget import NOW, Widget


def journal(backend: ContractBackend, shop: ShopId) -> list[AuditEntry]:
    with backend.uow(shop) as uow:
        return list(AuditLog.within(uow).search(AuditQuery(), PageRequest()).items)


def assert_not_written(backend: ContractBackend, shop: ShopId, widget: Widget) -> None:
    assert journal(backend, shop) == []
    with backend.uow(shop) as uow, pytest.raises(NotFound):
        widgets(uow).get(widget.id)


def test_auditable_event_is_journaled_with_the_action(
    backend: ContractBackend, shop_a: ShopId
) -> None:
    clock = FixedClock(NOW + timedelta(seconds=3))
    widget = widget_with(shop_a, WidgetAudited, WidgetIgnored)
    run_in_uow(backend, shop_a, lambda uow: widgets(uow).add(widget), [AuditRecorder(clock)])
    (written,) = journal(backend, shop_a)
    assert (written.action, written.performer.user_id, written.module) == (
        AuditAction.UPDATE,
        AUTHOR,
        "widgets",
    )
    assert (written.captured_at, written.received_at) == (NOW, clock.now())
    assert written.entity.id == widget.id.value
    assert not written.sensitive


def test_late_arrival_is_flagged_sensitive(backend: ContractBackend, shop_a: ShopId) -> None:
    clock = FixedClock(NOW + timedelta(hours=2))  # saisie hors connexion arrivée en retard
    widget = widget_with(shop_a, WidgetAudited)
    run_in_uow(backend, shop_a, lambda uow: widgets(uow).add(widget), [AuditRecorder(clock)])
    assert journal(backend, shop_a)[0].sensitive


def test_undecided_event_rolls_the_action_back(backend: ContractBackend, shop_a: ShopId) -> None:
    widget = widget_with(shop_a, WidgetAudited)
    widget.rename("x")  # WidgetRenamed : ni journalisable ni NotAudited
    with pytest.raises(UnauditedEvent, match="WidgetRenamed"):
        run_in_uow(
            backend, shop_a, lambda uow: widgets(uow).add(widget), [AuditRecorder(FixedClock(NOW))]
        )
    assert_not_written(backend, shop_a, widget)


def test_failing_translation_rolls_the_action_back(
    backend: ContractBackend, shop_a: ShopId
) -> None:
    widget = widget_with(shop_a, WidgetBroken)
    with pytest.raises(ValueError, match="traduction"):
        run_in_uow(
            backend, shop_a, lambda uow: widgets(uow).add(widget), [AuditRecorder(FixedClock(NOW))]
        )
    assert_not_written(backend, shop_a, widget)


def test_later_handler_failure_discards_the_journal_entry(
    backend: ContractBackend, shop_a: ShopId
) -> None:
    widget = widget_with(shop_a, WidgetAudited)
    handlers = [AuditRecorder(FixedClock(NOW)), FailingHandler()]
    with pytest.raises(HandlerFailure):
        run_in_uow(backend, shop_a, lambda uow: widgets(uow).add(widget), handlers)
    assert_not_written(backend, shop_a, widget)
