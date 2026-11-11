"""Lectures de disponibilité partagées par le grand livre et les écrans (RG-T17, UC-STK-09).

- `sellable_total` : stock vendable **tous lieux** d'un article (base de l'alerte de stock bas ;
  décision Q-18 : l'abîmé et l'en-route n'y entrent pas, on ne peut pas les vendre).
- `other_locations` : lieux **actifs** où l'article a du stock dans le même état, par ordre
  d'affichage (Q-43 : lieux à 0 exclus, entrepôts inclus — l'écran propose un déplacement).
"""

from collections.abc import Sequence
from decimal import Decimal

from app.application.ports.uow import UnitOfWork
from app.application.shops.ports import LocationRepository
from app.domain.shops.ids import LocationId
from app.domain.stock.errors import OtherLocation
from app.domain.stock.level import StockLevel
from app.domain.stock.values import StockCondition


def sellable_total(levels: Sequence[StockLevel]) -> Decimal:
    return sum((level.sellable.value for level in levels), Decimal(0))


def other_locations(
    uow: UnitOfWork,
    levels: Sequence[StockLevel],
    exclude: LocationId,
    condition: StockCondition,
) -> list[OtherLocation]:
    by_location = {level.location_id: level.balance(condition) for level in levels}
    found = []
    for location in LocationRepository.within(uow).list_all():
        quantity = by_location.get(location.id)
        if location.id == exclude or not location.active or quantity is None:
            continue
        if quantity.value > 0:
            found.append(OtherLocation(str(location.id), location.name, quantity))
    return found
