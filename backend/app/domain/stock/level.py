"""Projection `StockLevel` : stock d'un article dans un lieu (CDC § 20.2 « Stock par lieu », TR-13).

Un seul enregistrement par couple article x lieu (contrainte `stock_level_article_location`).
Trois soldes dans l'unité de stock de l'article : vendable, abîmé, en route vers ce lieu
(alimenté par les déplacements, Lot 2 : toujours 0 au Lot 1). Ils valent **la somme des
mouvements** (RG-T16) : seule `apply`, appelée par le grand livre avec le mouvement qu'elle
reflète, les change. La `version` (verrou optimiste, D6) arbitre deux sorties simultanées :
la seconde à valider échoue (`VersionConflict`) et rejoue avec le stock à jour.

La règle « jamais négatif en ligne » (RG-T17) est décidée par le grand livre, qui connaît le
mode (en ligne / différé) ; la projection, elle, accepte un solde négatif (RG-T18).
"""

from dataclasses import dataclass, field

from app.domain.catalog.ids import ArticleId
from app.domain.shared.events import EventCollector
from app.domain.shared.ids import ShopId
from app.domain.shared.quantity import Quantity, StockUnit
from app.domain.shops.ids import LocationId
from app.domain.stock.ids import StockLevelId
from app.domain.stock.values import StockCondition


@dataclass(eq=False, kw_only=True)
class StockLevel:
    id: StockLevelId
    shop_id: ShopId
    article_id: ArticleId
    location_id: LocationId
    sellable: Quantity
    damaged: Quantity
    incoming: Quantity
    version: int = 0
    events: EventCollector = field(default_factory=EventCollector, repr=False)

    def __post_init__(self) -> None:
        units = {self.sellable.unit, self.damaged.unit, self.incoming.unit}
        if len(units) != 1:
            msg = "StockLevel : soldes dans des unités différentes"
            raise ValueError(msg)

    @classmethod
    def empty(
        cls, shop_id: ShopId, article_id: ArticleId, location_id: LocationId, unit: StockUnit
    ) -> "StockLevel":
        zero = Quantity.zero(unit)
        return cls(
            id=StockLevelId.new(),
            shop_id=shop_id,
            article_id=article_id,
            location_id=location_id,
            sellable=zero,
            damaged=zero,
            incoming=zero,
        )

    @property
    def unit(self) -> StockUnit:
        return self.sellable.unit

    @property
    def key(self) -> tuple[ArticleId, LocationId]:
        return (self.article_id, self.location_id)

    @property
    def has_stock(self) -> bool:
        """Quantité non nulle quelque part : vendable, abîmée ou en route (UC-STK-04, UC-SOC-05)."""
        return any(q.value != 0 for q in (self.sellable, self.damaged, self.incoming))

    def balance(self, condition: StockCondition) -> Quantity:
        return self.sellable if condition is StockCondition.SELLABLE else self.damaged

    def apply(self, quantity: Quantity, condition: StockCondition) -> Quantity:
        """Ajoute `quantity` (signée) au solde de `condition` ; renvoie le nouveau solde."""
        updated = self.balance(condition) + quantity
        if condition is StockCondition.SELLABLE:
            self.sellable = updated
        else:
            self.damaged = updated
        return updated
