"""UC-STK-04 — Archiver ou réactiver un article (propriétaire seul ; recette CAT-11 à CAT-13).

Un article archivé disparaît des listes de vente et d'achat (recherche par défaut sur les
actifs) mais reste lisible : fiche, historique, rapports. Un article qui a encore du stock,
dans un lieu ou en route, ne peut pas être archivé (`ARTICLE_HAS_STOCK`, port `ArticleStock`,
provisoire jusqu'à T14). Archiver un article archivé, ou réactiver un actif, est une
transition refusée (`INVALID_STATE_TRANSITION`).
"""

from app.application.catalog.ports import ArticleRepository
from app.application.catalog.stock_probe import ArticleStock
from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWorkFactory
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop, performer_of
from app.domain.catalog.article import Article
from app.domain.catalog.errors import ArticleHasStock
from app.domain.catalog.ids import ArticleId


class ArchiveArticle:
    def __init__(
        self, uow_factory: UnitOfWorkFactory, policy: Policy, stock: ArticleStock, clock: Clock
    ) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._stock = stock
        self._clock = clock

    def archive(self, actor: Actor, article_id: ArticleId) -> Article:
        self._policy.require(actor, Permission.ARTICLE_ARCHIVE)
        with self._uow_factory(actor_shop(actor)) as uow:
            articles = ArticleRepository.within(uow)
            article = articles.get(article_id)
            if article.is_active and self._stock.has_stock(uow, article.id):
                raise ArticleHasStock(str(article.id))
            article.archive(performer=performer_of(actor), now=self._clock.now())
            articles.update(article)
            uow.commit()
        return article

    def reactivate(self, actor: Actor, article_id: ArticleId) -> Article:
        self._policy.require(actor, Permission.ARTICLE_ARCHIVE)
        with self._uow_factory(actor_shop(actor)) as uow:
            articles = ArticleRepository.within(uow)
            article = articles.get(article_id)
            article.reactivate(performer=performer_of(actor), now=self._clock.now())
            articles.update(article)
            uow.commit()
        return article
