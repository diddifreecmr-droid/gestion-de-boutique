"""Monde de test du catalogue : le monde du socle (`World`) + les cas d'utilisation du catalogue.

`stock` simule le port `ArticleStock` (articles « qui ont du stock ») en attendant T14.
"""

from dataclasses import dataclass, field

from app.application.catalog.ranking import SalesRanking
from app.application.catalog.stock_probe import ArticleStock
from app.application.catalog.use_cases.context import ArticleInput
from app.application.catalog.use_cases.create_article import CreateArticleCommand
from app.application.ports.uow import UnitOfWork
from app.application.security.actor import Actor
from app.application.shops.use_cases.open_shop import OpenShopCommand
from app.bootstrap.catalog import build_catalog
from app.domain.catalog.article import Article
from app.domain.catalog.ids import ArticleId
from app.domain.catalog.prices import ArticlePrices
from app.domain.shared.money import Money
from app.domain.shared.roles import Role
from tests.application.shops.support import World


class StockOf(ArticleStock):
    def __init__(self) -> None:
        self.stocked: set[ArticleId] = set()

    def has_stock(self, uow: UnitOfWork, article_id: ArticleId) -> bool:
        return article_id in self.stocked


@dataclass
class CatalogWorld(World):
    stock: StockOf = field(default_factory=StockOf)
    ranking: SalesRanking | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        self.catalog = build_catalog(self.identity, stock=self.stock, ranking=self.ranking).http

    def motos_owner(self) -> Actor:
        return self.owner(self.open_motos())

    def open_profile(self, profile_code: str, owner_phone: str = "690000009") -> Actor:
        command = OpenShopCommand(
            profile_code=profile_code,
            name=f"Boutique {profile_code}",
            city="Douala",
            phone="233000000",
            owner_name="Awa",
            owner_phone=owner_phone,
        )
        return self.owner(self.http.open_shop.execute(self.admin, command))

    def staff(self, owner: Actor, role: Role) -> Actor:
        phones = {Role.SELLER: "677000002", Role.ACCOUNTANT: "677000003", Role.DRIVER: "677000004"}
        location = "Garoua" if role is Role.SELLER else None
        return self.member(owner, phones[role], role, location)

    def moto(
        self,
        actor: Actor,
        model: str = "HJ125-8",
        brand: str = "Haojue",
        base_price: int | None = None,
        **fields: object,
    ) -> Article:
        prices = None if base_price is None else ArticlePrices(base_price=Money(base_price))
        command = CreateArticleCommand(
            data=ArticleInput(fields={"brand": brand, "model": model, **fields}), prices=prices
        )
        article, created = self.catalog.create.execute(actor, command)
        assert created
        return article

    def enable_min_price(self, owner: Actor) -> None:
        version = self.http.settings.get(owner).version
        self.http.settings.update(owner, {"min_price_enabled": True}, version)
