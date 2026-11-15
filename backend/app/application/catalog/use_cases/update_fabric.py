"""Modifier un tissu : prix, seuil, longueur du rouleau, « au mètre seulement » (2026-11-15).

La modification s'applique à **toutes** les couleurs du tissu, dans une transaction (une
couleur refusée → aucune modifiée) ; chacune garde son journal (avant/après) et son
historique des prix. Tissu sans couleur → 404.

- `patch` : `piece_length_m` (longueur du rouleau), `sold_by_piece` (faux = au mètre
  seulement), `alert_threshold` ; un champ absent ne change pas, `null` l'efface.
- `prices` : les quatre prix **remplacés** (comme `PUT /prices`) ; `None` = inchangés. Passer
  « au mètre seulement » retire les prix au rouleau devenus sans objet.
- Droits : `ARTICLE_WRITE` ; `PRICE_SET` (propriétaire) dès qu'un prix change. Pas de
  `version` par couleur : la dernière modification du tissu l'emporte (comme une saisie unique).
"""

from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from app.application.catalog.fabrics import FabricView, fabric_articles, require_fabrics
from app.application.catalog.ports import ArticleRepository
from app.application.catalog.use_cases.context import (
    ShopCatalogContext,
    build_details,
    record_history,
    shop_context,
)
from app.application.catalog.use_cases.update_article import merged_input
from app.application.catalog.visibility import visibility_for
from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWork, UnitOfWorkFactory
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop, performer_of
from app.domain.catalog.article import Article
from app.domain.catalog.prices import ArticlePrices
from app.domain.shared.errors import NotFound, ValidationFailed

FABRIC_FIELDS = frozenset({"piece_length_m", "sold_by_piece", "alert_threshold"})


def _without_roll_prices(prices: ArticlePrices) -> ArticlePrices:
    return replace(prices, base_price_piece=None, min_price_piece=None)


class UpdateFabric:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock

    def execute(
        self,
        actor: Actor,
        fabric: str,
        patch: Mapping[str, Any],
        prices: ArticlePrices | None = None,
    ) -> FabricView:
        self._policy.require(actor, Permission.ARTICLE_WRITE)
        unknown = sorted(set(patch) - FABRIC_FIELDS)
        if unknown:
            msg = "Champ non modifiable pour un tissu"
            raise ValidationFailed(msg, details={"fields": unknown})
        if prices is not None:
            self._policy.require(actor, Permission.PRICE_SET)
        with self._uow_factory(actor_shop(actor)) as uow:
            context = shop_context(uow)
            require_fabrics(context.profile)
            colors = fabric_articles(uow, fabric)
            if not colors:
                msg = "Tissu introuvable"
                raise NotFound(msg, details={"fabric": fabric})
            for article in colors:
                self._apply(uow, actor, context, article, patch, prices)
            uow.commit()
        return FabricView(
            fabric=colors[0].details.fields.fabric or fabric,
            articles=colors,
            visibility=visibility_for(self._policy, actor),
            min_price_enabled=context.settings.min_price_enabled,
            shop_threshold=context.settings.low_stock_threshold,
        )

    def _apply(
        self,
        uow: UnitOfWork,
        actor: Actor,
        context: ShopCatalogContext,
        article: Article,
        patch: Mapping[str, Any],
        prices: ArticlePrices | None,
    ) -> None:
        details = build_details(
            context.profile, merged_input(article.details, context.profile, patch)
        )
        by_roll = details.fields.sold_by_piece
        wanted = prices
        if (
            wanted is None
            and not by_roll
            and article.prices != _without_roll_prices(article.prices)
        ):
            self._policy.require(actor, Permission.PRICE_SET)
            wanted = _without_roll_prices(article.prices)
        performer, now = performer_of(actor), self._clock.now()

        def set_prices() -> bool:
            if wanted is None:
                return False
            changes = article.set_prices(
                wanted,
                min_price_enabled=context.settings.min_price_enabled,
                performer=performer,
                now=now,
            )
            record_history(uow, article, changes, author_id=actor.user_id, at=now)
            return bool(changes)

        def change() -> bool:
            return article.change(details, performer=performer, now=now)

        # Au mètre seulement : prix au rouleau retirés **avant** ; au rouleau : détails d'abord.
        steps = (change, set_prices) if by_roll else (set_prices, change)
        changed = [step() for step in steps]
        if any(changed):
            ArticleRepository.within(uow).update(article)
