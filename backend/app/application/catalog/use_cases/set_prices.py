"""UC-STK-03 — Fixer le prix de vente de base et le prix minimum (propriétaire seul ; CAT-08 à 10).

`PUT` : les quatre prix sont **remplacés** (un prix absent est retiré), avec la `version` lue
(409 sinon). Règles du domaine : montants ≥ 0, minimum ≤ base (`MIN_PRICE_ABOVE_BASE`), prix à
la pièce réservé à la vente à la pièce, minimum nouveau refusé si le réglage « prix minimum »
est désactivé (`MIN_PRICE_DISABLED`). Chaque prix changé ajoute une ligne à l'historique (date,
ancien, nouveau, auteur) ; le changement est journalisé et signalé comme sensible. Le nouveau
prix vaut pour les ventes suivantes, jamais pour les ventes passées (CAT-09, instantané T16).
"""

from app.application.catalog.ports import ArticleRepository
from app.application.catalog.use_cases.context import record_history, shop_context
from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWorkFactory
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop, performer_of, require_version
from app.domain.catalog.article import Article
from app.domain.catalog.ids import ArticleId
from app.domain.catalog.prices import ArticlePrices


class SetArticlePrices:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock

    def execute(
        self, actor: Actor, article_id: ArticleId, prices: ArticlePrices, version: int
    ) -> Article:
        self._policy.require(actor, Permission.PRICE_SET)
        now = self._clock.now()
        with self._uow_factory(actor_shop(actor)) as uow:
            articles = ArticleRepository.within(uow)
            article = articles.get(article_id)
            require_version(article.version, version)
            enabled = shop_context(uow).settings.min_price_enabled
            changes = article.set_prices(
                prices, min_price_enabled=enabled, performer=performer_of(actor), now=now
            )
            if changes:
                record_history(uow, article, changes, author_id=actor.user_id, at=now)
                articles.update(article)
                uow.commit()
        return article
