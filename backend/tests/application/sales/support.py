"""Monde de test des ventes : le monde des achats + le module Ventes assemblé (`build_sales`).

`record` enregistre une vente par le vrai cas d'utilisation ; `cash` / `credit` en sont les
raccourcis d'une ligne. `mode` lit l'identifiant d'un mode de paiement par son nom.
"""

from dataclasses import dataclass
from datetime import date

from app.application.sales.inputs import CustomerInput, LineInput, PaymentInput, SaleInput
from app.application.sales.use_cases.record_sale import RecordSaleCommand
from app.application.sales.views import SaleView
from app.application.security.actor import Actor
from app.application.shops.ports import PaymentModeRepository
from app.bootstrap.sales import build_sales
from app.domain.catalog.article import Article
from app.domain.sales.ids import SaleId
from app.domain.sales.lines import SoldDetail
from app.domain.sales.values import CreditTerms, SaleKind
from app.domain.shops.ids import PaymentModeId
from tests.application.purchasing.support import PurchasingWorld

MOUSSA = CustomerInput(name="Moussa A.", phone="+237690000000")


@dataclass
class SalesWorld(PurchasingWorld):
    def __post_init__(self) -> None:
        super().__post_init__()
        self.sales = build_sales(self.identity, self.ledger).http

    def mode(self, actor: Actor, name: str = "Espèces") -> PaymentModeId:
        with self.core.shop_uow_factory(self.shop_of(actor)) as uow:
            modes = PaymentModeRepository.within(uow).list_all()
        return next(mode.id for mode in modes if mode.name == name)

    def pay(self, actor: Actor, *amounts: tuple[str, int]) -> tuple[PaymentInput, ...]:
        return tuple(PaymentInput(mode_id=self.mode(actor, n), amount=a) for n, a in amounts)

    def line(  # type: ignore[override]
        self,
        article: Article,
        price: int,
        quantity: str | int = 1,
        *chassis: str,
    ) -> LineInput:
        details = tuple(SoldDetail(color="Rouge", chassis_number=c) for c in chassis)
        return LineInput(
            article_id=article.id, quantity=quantity, unit_price=price, details=details
        )

    def record(
        self,
        actor: Actor,
        *lines: LineInput,
        kind: SaleKind = SaleKind.CASH,
        payments: tuple[PaymentInput, ...] | None = None,
        customer: CustomerInput | None = None,
        sold_on: date | None = None,
        sale_id: SaleId | None = None,
        credit: CreditTerms | None = None,
    ) -> tuple[SaleView, bool]:
        if payments is None:
            total = sum(int(line.quantity) * line.unit_price for line in lines)
            payments = self.pay(actor, ("Espèces", total)) if total else ()
        data = SaleInput(
            kind=kind,
            lines=lines,
            payments=payments,
            customer=customer,
            sold_on=sold_on,
            location_id=self.loc(actor, "Garoua"),
            credit=credit,
        )
        return self.sales.record.execute(actor, RecordSaleCommand(data=data, sale_id=sale_id))

    def cash(self, actor: Actor, article: Article, price: int, *chassis: str) -> SaleView:
        view, created = self.record(actor, self.line(article, price, 1, *chassis))
        assert created
        return view

    def credit(
        self, actor: Actor, article: Article, price: int, deposit: int, *chassis: str
    ) -> SaleView:
        view, created = self.record(
            actor,
            self.line(article, price, 1, *chassis),
            kind=SaleKind.CREDIT,
            payments=self.pay(actor, ("Espèces", deposit)) if deposit else (),
            customer=MOUSSA,
        )
        assert created
        return view
