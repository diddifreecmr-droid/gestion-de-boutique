"""Boutique **X** « Tissus Ngaoundéré » de la recette du Lot 3 (§ 0) au niveau des cas
d'utilisation : propriétaire, employé, comptable ; article **WX** « Wax Fleur de mariage »
(unité Mètre, vente à la pièce, pièce 5,49 m, 2 500 /m et 13 000 /pièce)."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.application.catalog.use_cases.context import ArticleInput
from app.application.catalog.use_cases.create_article import CreateArticleCommand
from app.application.sales.inputs import LineInput, PaymentInput, SaleInput
from app.application.sales.use_cases.record_sale import RecordSaleCommand
from app.application.sales.views import SaleView
from app.application.security.actor import Actor
from app.domain.catalog.article import Article
from app.domain.catalog.prices import ArticlePrices
from app.domain.sales.lines import SaleMode
from app.domain.sales.values import SaleKind
from app.domain.shared.money import Money
from app.domain.shared.roles import Role
from tests.application.sales.support import SalesWorld

STORE = "Boutique"
WX_FIELDS = {
    "name": "Wax Fleur de mariage",
    "unit": "METER",
    "sold_by_piece": True,
    "piece_length_m": "5.49",
}


@dataclass
class TextileWorld(SalesWorld):
    def __post_init__(self) -> None:
        super().__post_init__()
        self.x_owner = self.open_profile("textile", owner_phone="690200001")
        self.employee = self.member(self.x_owner, "677200002", Role.SELLER, STORE)
        self.accountant = self.member(self.x_owner, "677200003", Role.ACCOUNTANT)

    def textile(self, fields: dict[str, object], prices: ArticlePrices | None = None) -> Article:
        command = CreateArticleCommand(data=ArticleInput(fields=fields), prices=prices)
        article, created = self.catalog.create.execute(self.x_owner, command)
        assert created
        return article

    def wax(self, **prices: int) -> Article:
        base = {"base_price": 2_500, "base_price_piece": 13_000} | prices
        return self.textile(WX_FIELDS, ArticlePrices(**{k: Money(v) for k, v in base.items()}))

    def sell(  # type: ignore[override]
        self,
        actor: Actor,
        article: Article,
        quantity: str,
        price: int,
        mode: SaleMode | None = None,
    ) -> SaleView:
        line = LineInput(article_id=article.id, quantity=quantity, unit_price=price, sale_mode=mode)
        total = int((Decimal(quantity) * price).quantize(Decimal(1), rounding=ROUND_HALF_UP))
        payment = PaymentInput(mode_id=self.mode(self.x_owner), amount=total)
        data = SaleInput(
            kind=SaleKind.CASH,
            lines=(line,),
            payments=(payment,) if total else (),
            location_id=self.loc(self.x_owner, STORE),
        )
        view, created = self.sales.record.execute(actor, RecordSaleCommand(data=data))
        assert created
        return view
