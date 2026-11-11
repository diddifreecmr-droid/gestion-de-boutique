"""Ports des demandes de prix et des retours (T16b), liés à la boutique.

- `PriceRequestRepository` : demandes d'un vendeur (portée OWN dans la requête), demandes au
  statut tenu « En attente », et demandes encore ouvertes (en attente ou acceptées non
  utilisées) dont l'échéance est passée — pour le worker d'expiration (TR-19).
- `SaleReturnRepository` : retours d'une vente (ordre de saisie) et retours **comptés** sur une
  période (`returned_on`, journées de Douala) pour le tableau de bord (T19, § 14.1).
"""

from abc import abstractmethod
from datetime import date, datetime

from app.application.shops.ports import ShopRecordRepository
from app.domain.sales.ids import PriceRequestId, SaleId, SaleReturnId
from app.domain.sales.price_request import PriceRequest
from app.domain.sales.sale_return import SaleReturn
from app.domain.shared.ids import UserId


class PriceRequestRepository(ShopRecordRepository[PriceRequestId, PriceRequest]):
    @abstractmethod
    def for_seller(self, seller: UserId) -> list[PriceRequest]:
        """Demandes du vendeur, plus récentes d'abord."""

    @abstractmethod
    def pending(self) -> list[PriceRequest]:
        """Demandes au statut tenu « En attente », plus récentes d'abord."""

    @abstractmethod
    def due_for_expiry(self, now: datetime) -> list[PriceRequest]:
        """En attente, ou acceptées sans vente liée, d'échéance `expires_at <= now`."""


class SaleReturnRepository(ShopRecordRepository[SaleReturnId, SaleReturn]):
    @abstractmethod
    def for_sale(self, sale_id: SaleId) -> list[SaleReturn]:
        """Retours de la vente, du plus ancien au plus récent."""

    @abstractmethod
    def between(self, first_day: date, last_day: date) -> list[SaleReturn]:
        """Retours faits pendant `[first_day, last_day]` (journées de Douala), plus anciens
        d'abord."""
