"""Monde de test des créances : le monde des ventes + le module Créances (`build_receivables`).

`scn01` reproduit SCN-01 étape 7 (§ 17.5) : 20 HJ achetées, puis vente à crédit de V à Moussa
(780 000, acompte 300 000) → créance 480 000. `versement` enregistre un versement par le vrai cas
d'utilisation.
"""

from dataclasses import dataclass
from datetime import date

from app.application.receivables.access import ReceivableView
from app.application.receivables.use_cases.record_installment import (
    InstallmentCommand,
    InstallmentResult,
)
from app.application.security.actor import Actor
from app.bootstrap.receivables import build_receivables
from app.domain.catalog.article import Article
from app.domain.purchasing.lines import FeeKind
from app.domain.receivables.ids import ReceivableId, receivable_id_for_sale
from app.domain.sales.ids import CustomerId
from tests.application.sales.support import SalesWorld


@dataclass
class ReceivablesWorld(SalesWorld):
    def __post_init__(self) -> None:
        super().__post_init__()
        self.receivables_module = build_receivables(self.identity)
        self.receivables = self.receivables_module.http

    def scn01(self) -> tuple[Actor, Actor, Actor, Article, ReceivableView]:
        owner, accountant, seller, hj = self.setup()
        self.buy(accountant, hj, 20, 520_000, fees=((FeeKind.CUSTOMS, 400_000, None),))
        hj = self.article(owner, hj)
        sale = self.credit(seller, hj, 780_000, 300_000).sale
        view = self.receivables.get.execute(owner, receivable_id_for_sale(sale.id))
        return owner, accountant, seller, hj, view

    def versement(
        self,
        actor: Actor,
        receivable_id: ReceivableId | None,
        amount: int,
        mode: str = "Espèces",
        *,
        customer_id: CustomerId | None = None,
        on: date | None = None,
    ) -> InstallmentResult:
        command = InstallmentCommand(
            amount=amount,
            mode_id=self.mode(actor, mode),
            receivable_id=receivable_id,
            customer_id=customer_id,
            paid_on=on,
        )
        result, created = self.receivables.record_installment.execute(actor, command)
        assert created
        return result

    def get(self, actor: Actor, receivable_id: ReceivableId) -> ReceivableView:
        return self.receivables.get.execute(actor, receivable_id)
