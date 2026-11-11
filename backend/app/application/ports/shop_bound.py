"""Base de tout port **lié à une boutique et à la transaction** d'une unité de travail (T09).

Deux familles en héritent :

- `Repository` : agrégats versionnés (`get`, `add`, `update`) ;
- les ports **sans agrégat**, comme le journal `AuditLog`, en ajout seul : ils n'héritent pas
  du gabarit `Repository`, donc n'ont ni `update` ni suppression (RG-J01, TR-09).

La boutique est un paramètre de construction ; l'instance s'obtient par `Port.within(uow)`,
qui renvoie l'adaptateur enregistré pour ce port dans la transaction de `uow`.
"""

from abc import ABC
from typing import TYPE_CHECKING, Protocol, Self

from app.domain.shared.ids import ShopId

if TYPE_CHECKING:
    from app.application.ports.aggregate import AggregateTracker


class PortProvider(Protocol):
    """Ce qu'offre une unité de travail aux ports : l'instance liée à sa transaction."""

    def repository_for(self, port: "type[ShopBoundPort]") -> "ShopBoundPort": ...


class ShopBoundPort(ABC):  # noqa: B024 — base commune, les méthodes abstraites sont dans les ports
    """Port lié à une boutique (`shop_id`) et à l'unité de travail qui le suit (`tracker`)."""

    def __init__(self, shop_id: ShopId, tracker: "AggregateTracker") -> None:
        if not isinstance(shop_id, ShopId):
            msg = f"Un dépôt est lié à un ShopId, reçu {type(shop_id).__name__}"
            raise TypeError(msg)
        self._shop_id = shop_id
        self._tracker = tracker

    @classmethod
    def within(cls, uow: PortProvider) -> Self:
        """Instance de ce port liée à la transaction et à la boutique de `uow`."""
        port = uow.repository_for(cls)
        if not isinstance(port, cls):
            msg = f"L'adaptateur fourni pour {cls.__name__} n'implémente pas ce port"
            raise TypeError(msg)
        return port

    @property
    def shop_id(self) -> ShopId:
        return self._shop_id
