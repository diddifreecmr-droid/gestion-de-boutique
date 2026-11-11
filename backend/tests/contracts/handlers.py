"""Handlers d'événements de test : enregistreur, journal (écrit dans la transaction), panne."""

from app.application.ports.event_handler import EventHandler
from app.application.ports.uow import UnitOfWork
from app.domain.shared.doc_number import DocType
from app.domain.shared.events import DomainEvent
from tests.contracts.widget import Widget, WidgetRenamed, WidgetRepository


class RecordingHandler(EventHandler):
    """Mémorise tout ce qui lui est remis, dans l'ordre."""

    def __init__(self) -> None:
        self.received: list[DomainEvent] = []

    def handle(self, event: DomainEvent, uow: UnitOfWork) -> None:
        self.received.append(event)


class JournalHandler(EventHandler):
    """Comme le futur journal : écrit, dans la même transaction, une entrée par renommage.

    L'entrée consomme un numéro `D` et produit elle-même un `WidgetCreated` (tour suivant).
    """

    def handle(self, event: DomainEvent, uow: UnitOfWork) -> None:
        if not isinstance(event, WidgetRenamed):
            return
        number = uow.numbering.next(DocType.EXPENSE)
        entry = Widget.create(uow.shop_id, f"journal:{event.label}", code=str(number))
        WidgetRepository.within(uow).add(entry)


class HandlerFailure(Exception):
    """Panne simulée d'un handler."""


class FailingHandler(EventHandler):
    def handle(self, event: DomainEvent, uow: UnitOfWork) -> None:
        msg = f"panne simulée sur {type(event).__name__}"
        raise HandlerFailure(msg)


class EndlessHandler(EventHandler):
    """Chaque événement en produit un autre : cascade sans fin, à arrêter."""

    def handle(self, event: DomainEvent, uow: UnitOfWork) -> None:
        WidgetRepository.within(uow).add(Widget.create(uow.shop_id, "écho"))
