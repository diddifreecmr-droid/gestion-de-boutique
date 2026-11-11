"""UC-STK-01 — Créer un article (propriétaire, comptable ; recette CAT-01 à CAT-03, M04, M05).

1. Champs du profil validés par le domaine (motos : marque et modèle ; nom affiché calculé).
2. Doublon (même marque + modèle, même référence, sans casse ni accent) → `DuplicateArticle`
   (409) qui désigne l'article existant : l'écran le propose.
3. Référence générée si le profil en a une et qu'elle est vide (`REF-000001`).
4. Prix facultatifs : **le propriétaire seul** les fixe (`PRICE_SET`) ; le comptable qui en
   envoie un reçoit 403 (CDC § 4.2 « sans le prix de vente », Q-14). Chaque prix fixé entre à
   l'historique des prix (ancien prix vide).

Idempotente : un `article_id` déjà connu de la boutique renvoie l'article existant
(`created=False`, specs § 6.1).
"""

from dataclasses import dataclass

from app.application.catalog.ports import ArticleRepository
from app.application.catalog.use_cases.context import (
    ArticleInput,
    build_details,
    ensure_reference,
    find_existing,
    record_history,
    require_unique,
    shop_context,
)
from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWorkFactory
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop, performer_of
from app.domain.catalog.article import Article
from app.domain.catalog.ids import ArticleId
from app.domain.catalog.prices import ArticlePrices


@dataclass(frozen=True, slots=True, kw_only=True)
class CreateArticleCommand:
    data: ArticleInput
    prices: ArticlePrices | None = None
    article_id: ArticleId | None = None


class CreateArticle:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock

    def execute(self, actor: Actor, command: CreateArticleCommand) -> tuple[Article, bool]:
        self._policy.require(actor, Permission.ARTICLE_WRITE)
        prices = command.prices
        if prices is not None and prices.set_kinds():
            self._policy.require(actor, Permission.PRICE_SET)
        performer, now = performer_of(actor), self._clock.now()
        with self._uow_factory(actor_shop(actor)) as uow:
            existing = find_existing(uow, command.article_id)
            if existing is not None:
                return existing, False
            context = shop_context(uow)
            articles = ArticleRepository.within(uow)
            details = build_details(context.profile, command.data)
            require_unique(articles, details)
            details = ensure_reference(uow, context.profile, details)
            article = Article.create(
                uow.shop_id, details, performer=performer, now=now, article_id=command.article_id
            )
            if prices is not None:
                changes = article.set_prices(
                    prices,
                    min_price_enabled=context.settings.min_price_enabled,
                    performer=performer,
                    now=now,
                )
                record_history(uow, article, changes, author_id=actor.user_id, at=now)
            articles.add(article)
            uow.commit()
        return article, True
