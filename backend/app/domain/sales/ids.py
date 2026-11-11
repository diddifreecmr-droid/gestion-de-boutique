"""Identifiants typés du module Ventes (UUIDv7 fournis par le client, specs § 6.1)."""

from app.domain.shared.ids import EntityId


class CustomerId(EntityId):
    """Client de la boutique (UC-VEN-11)."""

    __slots__ = ()


class SaleId(EntityId):
    """Vente `V-000001` (UC-VEN-01/02) ; source des mouvements « Sortie vente »."""

    __slots__ = ()


class SalePaymentId(EntityId):
    """Paiement noté à la vente (comptant ou acompte, RG-T20)."""

    __slots__ = ()


class ChassisClaimId(EntityId):
    """Réservation d'un numéro de châssis par une vente non annulée (RG-M01)."""

    __slots__ = ()


class ErrorReportId(EntityId):
    """Signalement d'erreur sur une vente (UC-VEN-06)."""

    __slots__ = ()


class ReceiptPrintId(EntityId):
    """Impression d'un reçu (UC-VEN-04, compteur « Duplicata »)."""

    __slots__ = ()


class PriceRequestId(EntityId):
    """Demande de prix sous le minimum (UC-VEN-03, T16b)."""

    __slots__ = ()


class SaleReturnId(EntityId):
    """Retour ou échange sur une vente (UC-VEN-09, T16b) ; source des « Retour client »."""

    __slots__ = ()
