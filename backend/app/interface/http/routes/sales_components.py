"""Cas d'utilisation du module Ventes, assemblés par la composition root (T16a)."""

from dataclasses import dataclass

from app.application.sales.use_cases.cancel_sale import CancelSale
from app.application.sales.use_cases.error_reports import AnswerErrorReport, ReportSaleError
from app.application.sales.use_cases.get_receipt import GetReceipt
from app.application.sales.use_cases.manage_customers import ManageCustomers
from app.application.sales.use_cases.modify_sale import ModifySale
from app.application.sales.use_cases.read_sales import GetSale, ListSales
from app.application.sales.use_cases.record_sale import RecordSale
from app.interface.http.security import AuthGuard


@dataclass(frozen=True, slots=True, kw_only=True)
class SalesComponents:
    record: RecordSale
    get: GetSale
    list: ListSales
    modify: ModifySale
    cancel: CancelSale
    report: ReportSaleError
    answer: AnswerErrorReport
    receipt: GetReceipt
    customers: ManageCustomers
    guard: AuthGuard
