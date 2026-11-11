"""UC-STK-05 — Consulter le stock : matrice article x lieu (recette STK-01 à STK-04).

- Une ligne par article **actif** ; une colonne par lieu **actif**, dans l'ordre d'affichage,
  puis « En route » (0 au Lot 1) et « Total » (vendable des colonnes affichées + en route).
- Recherche dès la première lettre (clé pliée du catalogue) ; filtre par lieu (une seule
  colonne) ; tri par nom ou par quantité (total affiché), croissant ou décroissant.
- Pastille (`StockBadge`) sur le stock vendable **tous lieux** : `out` à 0 ou moins (rouge,
  « Rupture »), `low` strictement sous le seuil appliqué (orange, Q-18), sinon `ok`.
- Ce que voit chaque rôle : `StockVisibility` (le présentateur n'en décide rien).
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.application.ports.uow import UnitOfWorkFactory
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop
from app.application.shops.ports import LocationRepository, ShopSettingsRepository
from app.application.stock.ports import StockLevelRepository
from app.application.stock.reading import all_articles
from app.application.stock.visibility import StockVisibility, stock_visibility
from app.domain.catalog.article import Article
from app.domain.catalog.details import ArticleStatus
from app.domain.catalog.ids import ArticleId
from app.domain.shared.quantity import Quantity
from app.domain.shops.ids import LocationId
from app.domain.shops.location import Location
from app.domain.stock.level import StockLevel


class MatrixOrder(StrEnum):
    NAME = "name"
    QUANTITY_ASC = "quantity_asc"
    QUANTITY_DESC = "quantity_desc"


class StockBadge(StrEnum):
    OK = "ok"
    LOW = "low"
    OUT = "out"


@dataclass(frozen=True, slots=True)
class MatrixCell:
    location_id: LocationId
    sellable: Quantity
    damaged: Quantity


@dataclass(frozen=True, slots=True, kw_only=True)
class MatrixRow:
    article: Article
    cells: list[MatrixCell]
    incoming: Quantity
    total: Quantity
    badge: StockBadge
    threshold: Decimal


@dataclass(frozen=True, slots=True, kw_only=True)
class StockMatrix:
    locations: list[Location]
    rows: list[MatrixRow]
    visibility: StockVisibility


def badge_for(total_sellable: Decimal, threshold: Decimal) -> StockBadge:
    if total_sellable <= 0:
        return StockBadge.OUT
    return StockBadge.LOW if total_sellable < threshold else StockBadge.OK


def _row(
    article: Article,
    levels: dict[tuple[ArticleId, LocationId], StockLevel],
    columns: list[Location],
    all_locations: list[Location],
    threshold: Decimal,
) -> MatrixRow:
    zero = Quantity.zero(article.details.fields.stock_unit)
    shown = [levels.get((article.id, loc.id)) for loc in columns]
    cells = [
        MatrixCell(loc.id, zero if lv is None else lv.sellable, zero if lv is None else lv.damaged)
        for loc, lv in zip(columns, shown, strict=True)
    ]
    incoming = sum((lv.incoming for lv in shown if lv is not None), zero)
    total = sum((cell.sellable for cell in cells), incoming)
    everywhere = sum(
        (lv.sellable.value for loc in all_locations if (lv := levels.get((article.id, loc.id)))),
        Decimal(0),
    )
    return MatrixRow(
        article=article,
        cells=cells,
        incoming=incoming,
        total=total,
        badge=badge_for(everywhere, threshold),
        threshold=threshold,
    )


class ReadStockMatrix:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy) -> None:
        self._uow_factory = uow_factory
        self._policy = policy

    def execute(
        self,
        actor: Actor,
        *,
        text: str | None = None,
        location_id: LocationId | None = None,
        order: MatrixOrder = MatrixOrder.NAME,
    ) -> StockMatrix:
        self._policy.require(actor, Permission.STOCK_READ)
        with self._uow_factory(actor_shop(actor)) as uow:
            locations = LocationRepository.within(uow)
            if location_id is not None:
                locations.get(location_id)  # NotFound si absent ou d'une autre boutique
            all_locations = locations.list_all()
            columns = [loc for loc in all_locations if loc.active]
            if location_id is not None:
                columns = [loc for loc in all_locations if loc.id == location_id]
            default = ShopSettingsRepository.within(uow).current().values.low_stock_threshold
            levels = {lv.key: lv for lv in StockLevelRepository.within(uow).list_all()}
            articles = all_articles(uow, text, ArticleStatus.ACTIVE)
        rows = [
            _row(a, levels, columns, all_locations, a.details.effective_threshold(default))
            for a in articles
        ]
        if order is not MatrixOrder.NAME:
            rows.sort(key=lambda row: row.total.value, reverse=order is MatrixOrder.QUANTITY_DESC)
        return StockMatrix(
            locations=columns, rows=rows, visibility=stock_visibility(self._policy, actor)
        )
