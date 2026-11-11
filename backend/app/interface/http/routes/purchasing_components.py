"""Cas d'utilisation du module Achats, assemblés par la composition root (T15)."""

from dataclasses import dataclass

from app.application.purchasing.use_cases.cancel_purchase import CancelPurchase
from app.application.purchasing.use_cases.correct_purchase import CorrectPurchase
from app.application.purchasing.use_cases.manage_suppliers import ManageSuppliers
from app.application.purchasing.use_cases.read_purchases import GetPurchase, ListPurchases
from app.application.purchasing.use_cases.record_payment import RecordSupplierPayment
from app.application.purchasing.use_cases.record_purchase import RecordPurchase
from app.interface.http.security import AuthGuard


@dataclass(frozen=True, slots=True, kw_only=True)
class PurchasingComponents:
    record: RecordPurchase
    correct: CorrectPurchase
    cancel: CancelPurchase
    pay: RecordSupplierPayment
    get: GetPurchase
    list: ListPurchases
    suppliers: ManageSuppliers
    guard: AuthGuard
