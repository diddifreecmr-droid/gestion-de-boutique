"""Monde de test des achats : le monde du stock + le module Achats assemblé (`build_purchasing`).

`buy` enregistre un achat d'une ligne par le vrai cas d'utilisation (avertissement de prix
confirmé par défaut) ; `at` place l'horloge un jour donné à 09 h (Douala) pour dater achats,
ventes et corrections comme dans la recette (SCN-04 : 01/11, 02/11, 03/11).
"""

from dataclasses import dataclass
from datetime import date, datetime, time

from app.application.catalog.ports import ArticleRepository
from app.application.purchasing.resolver import FeeInput, LineInput, PurchaseInput
from app.application.purchasing.use_cases.correct_purchase import CorrectPurchaseCommand
from app.application.purchasing.use_cases.record_purchase import RecordPurchaseCommand
from app.application.purchasing.views import PurchaseView
from app.application.security.actor import Actor
from app.bootstrap.purchasing import build_purchasing
from app.domain.catalog.article import Article
from app.domain.purchasing.lines import FeeKind
from app.domain.purchasing.units import EntryUnit
from app.domain.shared.business_day import BUSINESS_TZ
from tests.application.stock.support import StockWorld


def costs(world: StockWorld, actor: Actor, article: Article) -> tuple[int | None, int | None]:
    """(dernier coût, CMP) de l'article, relus en base."""
    with world.core.shop_uow_factory(world.shop_of(actor)) as uow:
        stored = ArticleRepository.within(uow).get(article.id)
    last, wac = stored.last_cost, stored.wac
    return (None if last is None else last.amount, None if wac is None else wac.amount)


@dataclass
class PurchasingWorld(StockWorld):
    def __post_init__(self) -> None:
        super().__post_init__()
        self.purchasing = build_purchasing(self.identity, self.ledger).http

    def at(self, day: date, hour: int = 9) -> None:
        self.clock.move_to(datetime.combine(day, time(hour), tzinfo=BUSINESS_TZ))

    def buy(
        self,
        actor: Actor,
        article: Article,
        quantity: str | int,
        price: int,
        *,
        on: date | None = None,
        where: str | None = "Garoua",
        unit: EntryUnit | None = None,
        fees: tuple[tuple[FeeKind, int, str | None], ...] = (),
        confirm: bool = True,
    ) -> PurchaseView:
        data = PurchaseInput(
            lines=(
                LineInput(article_id=article.id, quantity=quantity, unit_price=price, unit=unit),
            ),
            fees=tuple(FeeInput(kind=k, amount=a, label=label) for k, a, label in fees),
            purchase_date=on,
            location_id=None if where is None else self.loc(actor, where),
        )
        command = RecordPurchaseCommand(data=data, confirm_price_gap=confirm)
        view, created = self.purchasing.record.execute(actor, command)
        assert created
        return view

    def correct(
        self,
        actor: Actor,
        view: PurchaseView,
        reason: str = "faute de frappe",
        *,
        confirm: bool = False,
        **patch: object,
    ) -> PurchaseView:
        current = self.purchasing.get.execute(actor, view.purchase.id).purchase
        command = CorrectPurchaseCommand(
            purchase_id=current.id,
            version=current.version,
            reason=reason,
            patch=patch,
            confirm_price_gap=confirm,
        )
        return self.purchasing.correct.execute(actor, command)

    def line(self, article: Article, quantity: str | int, price: int) -> tuple[LineInput, ...]:
        return (LineInput(article_id=article.id, quantity=quantity, unit_price=price),)
