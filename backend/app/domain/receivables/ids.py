"""Identifiants typés du module Créances (UUIDv7, specs § 6.1).

La créance ouverte par une vente à crédit (UC-CRE-01) porte **l'identifiant de la vente**
(`receivable_id_for_sale`) : une seule créance par vente (CDC § 20.5), connue dès la saisie de
la vente (la réponse de vente expose `receivable.id` sans relire la créance).
"""

from app.domain.sales.ids import SaleId
from app.domain.shared.ids import EntityId


class ReceivableId(EntityId):
    """Créance (origine Vente ou Ancienne)."""

    __slots__ = ()


class InstallmentId(EntityId):
    """Versement `R-000001` (UC-CRE-03)."""

    __slots__ = ()


class ReminderId(EntityId):
    """Rappel de créance (UC-CRE-06)."""

    __slots__ = ()


class GuarantorId(EntityId):
    """Garant d'une créance (UC-CRE-07)."""

    __slots__ = ()


def receivable_id_for_sale(sale_id: SaleId) -> ReceivableId:
    """Identifiant de la créance née de `sale_id` (même UUID, type distinct)."""
    return ReceivableId(sale_id.value)
