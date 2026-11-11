"""Contrat des événements : remis aux handlers au commit, dans la transaction (D7, TR-09)."""

import pytest

from app.application.ports.errors import IsolationViolation, UnsavedChanges
from app.application.ports.uow import UnitOfWork
from app.domain.shared.doc_number import DocType
from app.domain.shared.errors import NotFound
from app.domain.shared.ids import ShopId
from tests.contracts.backends import ContractBackend
from tests.contracts.handlers import (
    EndlessHandler,
    FailingHandler,
    HandlerFailure,
    JournalHandler,
    RecordingHandler,
)
from tests.contracts.helpers import committed_widget, read_widget, run_in_uow, widgets
from tests.contracts.widget import NOW, Widget, WidgetCreated, WidgetRenamed


def test_events_are_delivered_only_at_commit_in_order(
    backend: ContractBackend, shop_a: ShopId
) -> None:
    recorder = RecordingHandler()
    first, second = Widget.create(shop_a, "un"), Widget.create(shop_a, "deux")
    with backend.uow(shop_a, [recorder]) as uow:
        widgets(uow).add(first)
        second.rename("deux bis")
        widgets(uow).add(second)
        assert recorder.received == []  # rien avant le commit
        uow.commit()
    received = [e for e in recorder.received if isinstance(e, WidgetCreated | WidgetRenamed)]
    assert len(received) == len(recorder.received)
    assert [(type(e), e.label) for e in received] == [
        (WidgetCreated, "un"),
        (WidgetCreated, "deux"),
        (WidgetRenamed, "deux bis"),
    ]
    assert len(first.events) == len(second.events) == 0  # retirés des agrégats


def test_rollback_delivers_nothing(backend: ContractBackend, shop_a: ShopId) -> None:
    recorder = RecordingHandler()
    with backend.uow(shop_a, [recorder]) as uow:
        widgets(uow).add(Widget.create(shop_a, "annulé"))
        uow.rollback()

    def fails(uow: UnitOfWork) -> None:
        widgets(uow).add(Widget.create(shop_a, "en échec"))
        raise RuntimeError

    with pytest.raises(RuntimeError):
        run_in_uow(backend, shop_a, fails, [recorder])
    assert recorder.received == []


def test_handler_writes_commit_with_the_transaction(
    backend: ContractBackend, shop_a: ShopId
) -> None:
    recorder = RecordingHandler()
    widget = committed_widget(backend, shop_a, "avant")
    with backend.uow(shop_a, [JournalHandler(), recorder]) as uow:
        loaded = widgets(uow).get(widget.id)
        loaded.rename("après")
        widgets(uow).update(loaded)
        uow.commit()
    renamed, journal_created = recorder.received  # l'entrée du journal émet au tour suivant
    assert isinstance(renamed, WidgetRenamed)
    assert isinstance(journal_created, WidgetCreated)
    assert journal_created.label == "journal:après"
    entry = read_widget(backend, shop_a, Widget(journal_created.widget_id, shop_a, "?"))
    assert entry.code == "D-000001"


def test_failing_handler_rolls_everything_back_and_reraises(
    backend: ContractBackend, shop_a: ShopId
) -> None:
    widget = committed_widget(backend, shop_a, "intact")
    added = Widget.create(shop_a, "jamais écrit")
    recorder = RecordingHandler()

    def use_case(uow: UnitOfWork) -> None:
        loaded = widgets(uow).get(widget.id)
        loaded.rename("modifié")
        widgets(uow).update(loaded)
        widgets(uow).add(added)
        uow.numbering.next(DocType.SALE)  # numéro attribué puis annulé avec le reste

    handlers = [recorder, JournalHandler(), FailingHandler()]
    with pytest.raises(HandlerFailure, match="panne simulée"):
        run_in_uow(backend, shop_a, use_case, handlers)
    assert len(recorder.received) == 1  # remis dans l'ordre, jusqu'à la panne
    assert read_widget(backend, shop_a, widget).label == "intact"
    with backend.uow(shop_a) as uow, pytest.raises(NotFound):
        widgets(uow).get(added.id)
    with backend.uow(shop_a) as uow:  # ni le numéro du cas d'utilisation, ni celui du journal
        assert str(uow.numbering.next(DocType.SALE)) == "V-000001"
        assert str(uow.numbering.next(DocType.EXPENSE)) == "D-000001"
        uow.commit()


def test_modified_but_unsaved_aggregate_fails_the_commit(
    backend: ContractBackend, shop_a: ShopId
) -> None:
    widget = committed_widget(backend, shop_a, "intact")

    def forgets_update(uow: UnitOfWork) -> None:
        widgets(uow).get(widget.id).rename("oublié")  # jamais repassé à update()

    with pytest.raises(UnsavedChanges):
        run_in_uow(backend, shop_a, forgets_update, [RecordingHandler()])
    assert read_widget(backend, shop_a, widget).label == "intact"


def test_event_of_another_shop_is_an_isolation_bug(
    backend: ContractBackend, shop_a: ShopId, shop_b: ShopId
) -> None:
    widget = Widget.create(shop_a, "a")
    widget.events.record(
        WidgetRenamed(shop_id=shop_b, occurred_at=NOW, widget_id=widget.id, label="fuite")
    )
    with pytest.raises(IsolationViolation):
        run_in_uow(backend, shop_a, lambda uow: widgets(uow).add(widget), [RecordingHandler()])
    with backend.uow(shop_a) as uow, pytest.raises(NotFound):
        widgets(uow).get(widget.id)


def test_endless_event_cascade_is_stopped(backend: ContractBackend, shop_a: ShopId) -> None:
    widget = Widget.create(shop_a, "graine")
    with pytest.raises(RuntimeError, match="cascade"):
        run_in_uow(backend, shop_a, lambda uow: widgets(uow).add(widget), [EndlessHandler()])
    with backend.uow(shop_a) as uow, pytest.raises(NotFound):
        widgets(uow).get(widget.id)
