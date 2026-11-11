"""UC-STK-10 — Consulter la valeur du stock (propriétaire, comptable ; recette VAL-01, SCN-09).

Par lieu et au total : quantité x CMP, et en vue complémentaire quantité x dernier coût. Le
stock **vendable** fait la valeur du stock (CDC § 14.1) ; l'**abîmé** et l'**en route** sont
valorisés à part. Coûts lus sur l'article (`wac`, `last_cost`, écrits par les Achats, T15).

« Non calculable » (RG-T15) : dès qu'un article en stock n'a pas de coût, la valeur exacte est
`None` (jamais 0) ; `Valuation` donne aussi la part connue et le nombre d'articles sans coût,
pour que l'écran dise « au moins X — N articles sans coût ».
"""

from collections.abc import Iterable
from dataclasses import dataclass

from app.application.ports.uow import UnitOfWorkFactory
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop
from app.application.stock.ports import StockLevelRepository
from app.application.stock.reading import articles_by_id, locations_by_id
from app.domain.catalog.article import Article
from app.domain.catalog.ids import ArticleId
from app.domain.shared.money import Money
from app.domain.shared.quantity import Quantity
from app.domain.shops.location import Location
from app.domain.stock.level import StockLevel
from app.domain.stock.valuation import value_of

type Holding = tuple[Article, Quantity]


@dataclass(frozen=True, slots=True, kw_only=True)
class Valuation:
    at_wac: Money | None
    at_wac_known: Money
    without_wac: int
    at_last_cost: Money | None
    at_last_cost_known: Money
    without_last_cost: int


def valuation(holdings: Iterable[Holding]) -> Valuation:
    wac_known, last_known = Money.zero(), Money.zero()
    without_wac = without_last = 0
    for article, quantity in holdings:
        if quantity.value == 0:
            continue
        at_wac, at_last = value_of(quantity, article.wac), value_of(quantity, article.last_cost)
        if at_wac is None:
            without_wac += 1
        else:
            wac_known += at_wac
        if at_last is None:
            without_last += 1
        else:
            last_known += at_last
    return Valuation(
        at_wac=None if without_wac else wac_known,
        at_wac_known=wac_known,
        without_wac=without_wac,
        at_last_cost=None if without_last else last_known,
        at_last_cost_known=last_known,
        without_last_cost=without_last,
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class LocationValue:
    location: Location
    sellable: Valuation
    damaged: Valuation
    incoming: Valuation


@dataclass(frozen=True, slots=True, kw_only=True)
class StockValueReport:
    locations: list[LocationValue]
    sellable: Valuation
    damaged: Valuation
    incoming: Valuation


def _split(
    levels: list[StockLevel], articles: dict[ArticleId, Article]
) -> tuple[list[Holding], list[Holding], list[Holding]]:
    known = [(articles[lv.article_id], lv) for lv in levels if lv.article_id in articles]
    return (
        [(a, lv.sellable) for a, lv in known],
        [(a, lv.damaged) for a, lv in known],
        [(a, lv.incoming) for a, lv in known],
    )


class ReadStockValue:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy) -> None:
        self._uow_factory = uow_factory
        self._policy = policy

    def execute(self, actor: Actor) -> StockValueReport:
        self._policy.require(actor, Permission.STOCK_VALUE_READ)
        with self._uow_factory(actor_shop(actor)) as uow:
            levels = StockLevelRepository.within(uow).list_all()
            articles: dict[ArticleId, Article] = articles_by_id(uow)
            locations = locations_by_id(uow)
        rows = []
        for location in locations.values():
            mine = [lv for lv in levels if lv.location_id == location.id]
            if not location.active and not any(lv.has_stock for lv in mine):
                continue
            sellable, damaged, incoming = _split(mine, articles)
            rows.append(
                LocationValue(
                    location=location,
                    sellable=valuation(sellable),
                    damaged=valuation(damaged),
                    incoming=valuation(incoming),
                )
            )
        sellable, damaged, incoming = _split(levels, articles)
        return StockValueReport(
            locations=rows,
            sellable=valuation(sellable),
            damaged=valuation(damaged),
            incoming=valuation(incoming),
        )
