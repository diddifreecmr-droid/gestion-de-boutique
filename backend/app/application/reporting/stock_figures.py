"""Bloc « Stock » du tableau de bord et de l'accueil du comptable (UC-TDB-01 point 4, UC-TDB-05).

État **actuel**, lu sur la projection `stock_level` (specs § 10, jamais la somme des mouvements) :

- **Valeur du stock** (§ 14.1) : quantité vendable x CMP, tous lieux, par la même fonction que
  UC-STK-10 (`valuation`) ; vue au dernier coût à côté ; abîmé valorisé à part ; `None` + nombre
  d'articles sans coût si un coût manque (RG-T15, jamais 0).
- **Alertes de stock bas** : articles actifs dont le stock vendable tous lieux est
  **strictement** sous le seuil appliqué (Q-18) — la règle de l'alerte UC-STK-09.
- **Stock à vérifier** (RG-T18) : couples article x lieu au stock vendable négatif.
- **Déplacements en route** : Lot 2, renvoyés « non disponible » par le cas d'utilisation.
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from app.application.ports.uow import UnitOfWork
from app.application.shops.ports import ShopSettingsRepository
from app.application.stock.ports import StockLevelRepository
from app.application.stock.reading import all_articles, articles_by_id
from app.application.stock.use_cases.stock_value import Valuation, valuation
from app.domain.catalog.article import Article
from app.domain.catalog.details import ArticleStatus
from app.domain.catalog.ids import ArticleId
from app.domain.stock.level import StockLevel


@dataclass(frozen=True, slots=True, kw_only=True)
class StockFigures:
    sellable: Valuation
    damaged: Valuation
    low_stock: int
    to_verify: int


@dataclass(frozen=True, slots=True, kw_only=True)
class LowStock:
    article: Article
    quantity: Decimal
    threshold: Decimal


def low_stock_of(
    articles: Iterable[Article], levels: Iterable[StockLevel], default: Decimal
) -> list[LowStock]:
    """Articles actifs sous le seuil (strict, Q-18), dans l'ordre reçu (par nom)."""
    everywhere: dict[ArticleId, Decimal] = defaultdict(Decimal)
    for level in levels:
        everywhere[level.article_id] += level.sellable.value
    found = []
    for article in articles:
        threshold = article.details.effective_threshold(default)
        quantity = everywhere[article.id]
        if article.status is ArticleStatus.ACTIVE and quantity < threshold:
            found.append(LowStock(article=article, quantity=quantity, threshold=threshold))
    return found


def low_stock_in(uow: UnitOfWork) -> list[LowStock]:
    default = ShopSettingsRepository.within(uow).current().values.low_stock_threshold
    levels = StockLevelRepository.within(uow).list_all()
    return low_stock_of(all_articles(uow, status=ArticleStatus.ACTIVE), levels, default)


def stock_figures(uow: UnitOfWork) -> StockFigures:
    """Figures du stock de la boutique de `uow` (à lire dans une transaction ouverte)."""
    levels = StockLevelRepository.within(uow).list_all()
    articles = articles_by_id(uow)
    default = ShopSettingsRepository.within(uow).current().values.low_stock_threshold
    known = [lv for lv in levels if lv.article_id in articles]
    return StockFigures(
        sellable=valuation((articles[lv.article_id], lv.sellable) for lv in known),
        damaged=valuation((articles[lv.article_id], lv.damaged) for lv in known),
        low_stock=len(low_stock_of(articles.values(), known, default)),
        to_verify=sum(1 for lv in known if lv.sellable.value < 0),
    )
