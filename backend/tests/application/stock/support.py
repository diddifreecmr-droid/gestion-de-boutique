"""Monde de test du stock : le monde du catalogue + le module Stock assemblé (`build_stock`).

`stock_in` poste une « Reprise de départ » par le vrai grand livre (comme le fera un achat,
T15) ; `set_costs` écrit le dernier coût et le CMP comme le module Achats.
"""

from dataclasses import dataclass
from decimal import Decimal
from uuid import uuid4

from app.application.alerts.ports import AlertRepository
from app.application.catalog.ports import ArticleRepository
from app.application.ports.pagination import PageRequest
from app.application.security.actor import Actor
from app.application.stock.adjusting import AdjustmentResult
from app.application.stock.postings import Posting
from app.application.stock.use_cases.record_adjustment import AdjustmentCommand
from app.bootstrap.catalog import build_catalog
from app.bootstrap.stock import build_stock
from app.domain.alerts.alert import Alert
from app.domain.catalog.article import Article
from app.domain.shared.money import Money
from app.domain.shared.quantity import Quantity
from app.domain.shared.roles import Role
from app.domain.shops.ids import LocationId
from app.domain.stock.adjustment import AdjustmentDirection, AdjustmentReason
from app.domain.stock.ids import AdjustmentId
from app.domain.stock.movement import StockMovement
from app.domain.stock.values import MovementType, SourceRef, SourceType, StockCondition
from app.interface.http.routes.catalog import CatalogComponents
from tests.application.catalog.support import CatalogWorld


@dataclass
class StockWorld(CatalogWorld):
    def __post_init__(self) -> None:
        super().__post_init__()
        self.stock_module = build_stock(self.identity)
        self.ledger = self.stock_module.ledger
        self.stock_http = self.stock_module.http

    def setup(self) -> tuple[Actor, Actor, Actor, Article]:
        """Propriétaire, comptable, vendeur et la moto HJ125-8 (seuil 5)."""
        owner = self.motos_owner()
        accountant = self.staff(owner, Role.ACCOUNTANT)
        seller = self.staff(owner, Role.SELLER)
        article = self.moto(owner, base_price=780_000, alert_threshold=None)
        return owner, accountant, seller, article

    def moto(  # type: ignore[override]
        self,
        actor: Actor,
        model: str = "HJ125-8",
        brand: str = "Haojue",
        base_price: int | None = None,
        alert_threshold: Decimal | None = Decimal(5),
        **fields: object,
    ) -> Article:
        article = super().moto(actor, model, brand, base_price, **fields)
        if alert_threshold is not None:
            self.catalog.update.execute(
                actor, article.id, {"alert_threshold": alert_threshold}, article.version
            )
        return self.article(actor, article)

    def article(self, actor: Actor, article: Article) -> Article:
        with self.core.shop_uow_factory(self.shop_of(actor)) as uow:
            return ArticleRepository.within(uow).get(article.id)

    def loc(self, actor: Actor, name: str) -> LocationId:
        return self.location_id(self.shop_of(actor), name)

    def stock_in(
        self, actor: Actor, article: Article, where: str, quantity: int | str, cost: int = 500_000
    ) -> StockMovement:
        posting = Posting(
            article_id=article.id,
            location_id=self.loc(actor, where),
            type=MovementType.OPENING,
            quantity=Quantity.of(quantity, article.details.fields.stock_unit),
            source=SourceRef(SourceType.IMPORT, uuid4()),
            occurred_at=self.clock.now(),
            author_id=actor.user_id,
            unit_cost=Money(cost),
        )
        with self.core.shop_uow_factory(self.shop_of(actor)) as uow:
            movement = self.ledger.record_entry(uow, posting)
            uow.commit()
        return movement

    def sell(
        self, actor: Actor, article: Article, where: str, quantity: int, *, deferred: bool = False
    ) -> StockMovement:
        posting = Posting(
            article_id=article.id,
            location_id=self.loc(actor, where),
            type=MovementType.SALE_OUT,
            quantity=Quantity.of(quantity, article.details.fields.stock_unit),
            source=SourceRef(SourceType.SALE, uuid4(), "V-000001"),
            occurred_at=self.clock.now(),
            author_id=actor.user_id,
        )
        with self.core.shop_uow_factory(self.shop_of(actor)) as uow:
            movement = self.ledger.record_exit(uow, posting, deferred=deferred)
            uow.commit()
        return movement

    def set_costs(self, actor: Actor, article: Article, last: int | None, wac: int | None) -> None:
        with self.core.shop_uow_factory(self.shop_of(actor)) as uow:
            articles = ArticleRepository.within(uow)
            stored = articles.get(article.id)
            stored.record_costs(
                last_cost=None if last is None else Money(last),
                wac=None if wac is None else Money(wac),
            )
            articles.update(stored)
            uow.commit()

    def adjust(
        self,
        actor: Actor,
        article: Article,
        where: str,
        quantity: str,
        direction: AdjustmentDirection = AdjustmentDirection.OUT,
        reason: AdjustmentReason = AdjustmentReason.BREAKAGE,
        *,
        condition: StockCondition = StockCondition.SELLABLE,
        note: str | None = None,
        adjustment_id: AdjustmentId | None = None,
    ) -> AdjustmentResult:
        command = AdjustmentCommand(
            location_id=self.loc(actor, where),
            article_id=article.id,
            direction=direction,
            quantity=quantity,
            condition=condition,
            reason=reason,
            note=note,
            adjustment_id=adjustment_id,
        )
        return self.stock_http.adjust.execute(actor, command)

    def matrix_total(self, actor: Actor, article: Article) -> str:
        rows = self.stock_http.matrix.execute(actor).rows
        return str(next(row.total for row in rows if row.article.id == article.id))

    def movements(self, actor: Actor, article: Article) -> list[StockMovement]:
        history = self.stock_http.movements.execute(actor, article.id, PageRequest())
        return list(history.page.items)

    def alerts(self, shop_actor: Actor, recipient: Actor) -> list[Alert]:
        with self.core.shop_uow_factory(self.shop_of(shop_actor)) as uow:
            page = AlertRepository.within(uow).for_recipient(recipient.user_id, PageRequest())
            return list(page.items)

    def shops_catalog(self) -> CatalogComponents:
        """Catalogue assemblé avec la vraie sonde de stock (`LedgerArticleStock`)."""
        return build_catalog(self.identity).http
