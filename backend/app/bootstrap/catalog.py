"""Assemblage du catalogue (T13) : articles, prix, archivage, recherche.

- `ArticleStock` : `LedgerArticleStock` du module Stock (T14), sur la projection `stock_level`
  (les tests peuvent en injecter un autre).
- `SalesRanking` : servi par le module Ventes (`bootstrap/sales.sales_ranking`, T16) ; absent
  (outils, tests ciblés), le tri « plus vendus » répond 400 `SORT_UNAVAILABLE`.
- `LinkSigner` : celui des pièces jointes (`bootstrap/attachments`), pour les vignettes de la
  liste (T30) ; absent, `with_thumbnails=true` répond 400 `THUMBNAILS_UNAVAILABLE`.
"""

from dataclasses import dataclass

from app.application.attachments.links import LinkSigner
from app.application.catalog.ranking import SalesRanking
from app.application.catalog.stock_probe import ArticleStock
from app.application.catalog.thumbnails import ArticleThumbnails
from app.application.catalog.use_cases.archive_article import ArchiveArticle
from app.application.catalog.use_cases.create_article import CreateArticle
from app.application.catalog.use_cases.read_articles import GetArticle, SearchArticles
from app.application.catalog.use_cases.set_prices import SetArticlePrices
from app.application.catalog.use_cases.update_article import UpdateArticle
from app.application.security.policy import Policy
from app.application.stock.probes import LedgerArticleStock
from app.bootstrap.identity import IdentityModule
from app.interface.http.routes.catalog import CatalogComponents


@dataclass(frozen=True, slots=True, kw_only=True)
class CatalogModule:
    http: CatalogComponents


def build_catalog(
    identity: IdentityModule,
    *,
    stock: ArticleStock | None = None,
    ranking: SalesRanking | None = None,
    signer: LinkSigner | None = None,
) -> CatalogModule:
    uows, clock = identity.core.shop_uow_factory, identity.clock
    policy = Policy(clock=clock.now)
    thumbnails = None if signer is None else ArticleThumbnails(policy, clock, signer)
    http = CatalogComponents(
        create=CreateArticle(uows, policy, clock),
        update=UpdateArticle(uows, policy, clock),
        prices=SetArticlePrices(uows, policy, clock),
        archive=ArchiveArticle(uows, policy, stock or LedgerArticleStock(), clock),
        search=SearchArticles(uows, policy, ranking, thumbnails),
        get=GetArticle(uows, policy),
        guard=identity.auth.guard,
    )
    return CatalogModule(http=http)
