"""Assemblage du module Achats (T15) : fournisseurs, achats, Costing, paiements.

Les achats postent leurs entrées par **le** grand livre de l'application
(`StockModule.ledger`, un seul par application) dans leur propre transaction ; les unités de
travail sont celles du noyau (journal et alertes branchés, TR-09).
"""

from dataclasses import dataclass

from app.application.purchasing.use_cases.cancel_purchase import CancelPurchase
from app.application.purchasing.use_cases.correct_purchase import CorrectPurchase
from app.application.purchasing.use_cases.manage_suppliers import ManageSuppliers
from app.application.purchasing.use_cases.read_purchases import GetPurchase, ListPurchases
from app.application.purchasing.use_cases.record_payment import RecordSupplierPayment
from app.application.purchasing.use_cases.record_purchase import RecordPurchase
from app.application.security.policy import Policy
from app.application.stock.ledger import StockLedger
from app.bootstrap.identity import IdentityModule
from app.interface.http.routes.purchasing_components import PurchasingComponents


@dataclass(frozen=True, slots=True, kw_only=True)
class PurchasingModule:
    http: PurchasingComponents


def build_purchasing(identity: IdentityModule, ledger: StockLedger) -> PurchasingModule:
    uows, clock = identity.core.shop_uow_factory, identity.clock
    policy = Policy(clock=clock.now)
    http = PurchasingComponents(
        record=RecordPurchase(uows, policy, ledger, clock),
        correct=CorrectPurchase(uows, policy, ledger, clock),
        cancel=CancelPurchase(uows, policy, ledger, clock),
        pay=RecordSupplierPayment(uows, policy, clock),
        get=GetPurchase(uows, policy, clock),
        list=ListPurchases(uows, policy, clock),
        suppliers=ManageSuppliers(uows, policy, clock),
        guard=identity.auth.guard,
    )
    return PurchasingModule(http=http)
