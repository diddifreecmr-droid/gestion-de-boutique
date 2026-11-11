"""Assemblage du module Ventes (T16a) : clients, ventes, signalements, reçus, classement.

- Les ventes postent leurs sorties par **le** grand livre de l'application
  (`StockModule.ledger`) dans leur propre transaction (journal et alertes branchés, TR-09).
- `CustomerDebt` : `ReceivableCustomerDebt` (restes des créances En cours, T17).
- `ranking` : le port `SalesRanking` servi au catalogue (`sort=best_selling`, 30 jours).
- Les règles d'alerte « Erreur signalée » et « Demande de prix » sont branchées par le noyau
  (`bootstrap/core.py`).
- T16b : demandes de prix, retours / échanges (l'échange réutilise **le même** `RecordSale`) ;
  `expire_price_requests` : tâche planifiée du futur worker (TR-19), par boutique.
"""

from dataclasses import dataclass

from app.application.catalog.ranking import SalesRanking
from app.application.ports.clock import Clock
from app.application.receivables.debt import ReceivableCustomerDebt
from app.application.sales.ranking import LedgerSalesRanking
from app.application.sales.use_cases.cancel_sale import CancelSale
from app.application.sales.use_cases.error_reports import AnswerErrorReport, ReportSaleError
from app.application.sales.use_cases.expire_price_requests import ExpirePriceRequests
from app.application.sales.use_cases.get_receipt import GetReceipt
from app.application.sales.use_cases.manage_customers import ManageCustomers
from app.application.sales.use_cases.modify_sale import ModifySale
from app.application.sales.use_cases.price_requests import (
    DecidePriceRequest,
    GetPriceRequest,
    ListPriceRequests,
    RequestPriceApproval,
)
from app.application.sales.use_cases.read_returns import ListSaleReturns
from app.application.sales.use_cases.read_sales import GetSale, ListSales
from app.application.sales.use_cases.record_return import RecordReturn
from app.application.sales.use_cases.record_sale import RecordSale
from app.application.security.policy import Policy
from app.application.stock.ledger import StockLedger
from app.bootstrap.identity import IdentityModule
from app.interface.http.routes.sales_components import SalesComponents


@dataclass(frozen=True, slots=True, kw_only=True)
class SalesModule:
    http: SalesComponents
    expire_price_requests: ExpirePriceRequests


def sales_ranking(clock: Clock) -> SalesRanking:
    """Tri « plus vendus » du catalogue (à passer à `build_catalog(..., ranking=...)`)."""
    return LedgerSalesRanking(clock)


def build_sales(identity: IdentityModule, ledger: StockLedger) -> SalesModule:
    core, clock = identity.core, identity.clock
    uows = core.shop_uow_factory
    policy = Policy(clock=clock.now)
    record = RecordSale(uows, policy, ledger, clock, ReceivableCustomerDebt())
    http = SalesComponents(
        record=record,
        get=GetSale(uows, policy),
        list=ListSales(uows, policy, clock),
        modify=ModifySale(uows, policy, clock),
        cancel=CancelSale(uows, policy, ledger, clock),
        report=ReportSaleError(uows, policy, clock),
        answer=AnswerErrorReport(uows, policy, clock),
        receipt=GetReceipt(uows, core.platform_uow_factory, policy, clock),
        customers=ManageCustomers(uows, policy, clock),
        request_price=RequestPriceApproval(uows, policy, clock),
        decide_price=DecidePriceRequest(uows, policy, clock),
        list_price_requests=ListPriceRequests(uows, policy, clock),
        get_price_request=GetPriceRequest(uows, policy, clock),
        record_return=RecordReturn(uows, policy, ledger, clock, record),
        list_returns=ListSaleReturns(uows, policy),
        guard=identity.auth.guard,
    )
    return SalesModule(http=http, expire_price_requests=ExpirePriceRequests(uows))
