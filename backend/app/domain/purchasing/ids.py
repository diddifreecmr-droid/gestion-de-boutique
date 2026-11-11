"""Identifiants typés du module Achats (UUIDv7 fournis par le client, specs § 6.1)."""

from app.domain.shared.ids import EntityId


class SupplierId(EntityId):
    """Fournisseur (UC-ACH-02)."""

    __slots__ = ()


class PurchaseId(EntityId):
    """Achat `A-000001` (UC-ACH-01) ; source des mouvements « Entrée achat »."""

    __slots__ = ()


class SupplierPaymentId(EntityId):
    """Paiement noté sur un achat (UC-ACH-06)."""

    __slots__ = ()
