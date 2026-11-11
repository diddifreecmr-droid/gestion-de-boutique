"""Raccourcis des tests de contrat (n'utilisent que les ports : valables pour tout adaptateur)."""

from collections.abc import Callable, Sequence

from app.application.ports.event_handler import EventHandler
from app.application.ports.uow import UnitOfWork
from app.domain.shared.ids import ShopId
from tests.contracts.backends import ContractBackend
from tests.contracts.widget import Widget, WidgetRepository


def run_in_uow(
    backend: ContractBackend,
    shop_id: ShopId,
    action: Callable[[UnitOfWork], object],
    handlers: Sequence[EventHandler] = (),
) -> None:
    """Forme d'un cas d'utilisation : une transaction, `action`, puis `commit()`.

    Sert à `pytest.raises(...)` : l'erreur attendue peut venir de l'écriture **ou** du commit,
    selon l'adaptateur ; le contrat n'impose que « rien n'est écrit ».
    """
    with backend.uow(shop_id, handlers) as uow:
        action(uow)
        uow.commit()


def committed_widget(
    backend: ContractBackend, shop_id: ShopId, label: str = "w", code: str | None = None
) -> Widget:
    """Crée et valide un widget ; renvoie l'instance de l'appelant (version 1)."""
    widget = Widget.create(shop_id, label, code=code)
    run_in_uow(backend, shop_id, lambda uow: widgets(uow).add(widget))
    return widget


def read_widget(backend: ContractBackend, shop_id: ShopId, widget: Widget) -> Widget:
    """Relit un widget dans une transaction neuve (lecture seule)."""
    with backend.uow(shop_id) as uow:
        return WidgetRepository.within(uow).get(widget.id)


def widgets(uow: UnitOfWork) -> WidgetRepository:
    return WidgetRepository.within(uow)
