"""Port de requête `DashboardQueries` (TR-21, specs § 10) : agrégats en lecture seule par journée.

Le port ne calcule **aucun indicateur** : il rend des sommes brutes par journée de Douala, que
`indicators.py` (seul endroit qui définit le CDC § 14.1) combine. Ainsi les adaptateurs mémoire
et SQL n'ont qu'une sémantique simple à respecter (`tests/contracts/test_reporting_contract.py`).

Journée de rattachement de chaque somme (Q-09 : une annulation compte **le jour où elle est
faite**, une journée passée ne bouge jamais) :

- ventes et lignes : `sold_on` de la vente, **annulées comprises** (`sales_by_day`) ;
- annulations de vente : journée de `cancelled_at` (`cancelled_by_day`, mêmes sommes) ;
- retours : `returned_on` (montant et marges aux coûts figés, T16b) ;
- argent (`money_flows`) : paiements de vente au `sold_on` (comptant / acompte), payé des ventes
  annulées au jour de l'annulation, versements au `paid_on` (annulés compris), versements
  annulés au jour de l'annulation, remboursements de retour au `refunded_on` ;
- dépenses (`expense_flows`) : `spent_on` (annulées comprises) et annulations au jour de
  `cancelled_at`.

`seller` restreint la requête aux ventes de ce vendeur (portée « Siens », accueil vendeur) ;
`responsible` aux créances dont il est le vendeur responsable (Q-21). Les états (créances,
alertes en attente) sont lus **maintenant** : ils ne sont pas historisés au Lot 1.
"""

from abc import abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from app.application.ports.shop_bound import ShopBoundPort
from app.domain.shared.ids import UserId
from app.domain.shops.ids import ExpenseCategoryId, PaymentModeId


@dataclass(frozen=True, slots=True, kw_only=True)
class SalesDay:
    """Sommes des ventes d'une journée (ou des ventes annulées ce jour-là)."""

    day: date
    count: int = 0
    total: int = 0
    margin: int = 0
    """Somme des marges **connues** au dernier coût figé (lignes à marge nulle exclues)."""
    margin_wac: int = 0
    without_cost: int = 0
    """Lignes à marge au dernier coût non calculable (RG-T15)."""
    without_wac: int = 0


@dataclass(frozen=True, slots=True, kw_only=True)
class ReturnsDay:
    day: date
    count: int = 0
    amount: int = 0
    margin: int = 0
    margin_wac: int = 0
    without_cost: int = 0
    """Retours dont la marge n'est pas calculable (une ligne sans coût figé)."""


class FlowKind(StrEnum):
    """Nature d'un mouvement d'argent (RG-T21) ; `sign` dit s'il entre ou sort."""

    SALE_CASH = "sale_cash"  # Paiement comptant
    SALE_DEPOSIT = "sale_deposit"  # Acompte d'une vente à crédit
    SALE_CANCELLED = "sale_cancelled"  # Payé d'une vente annulée ce jour (Q-09)
    INSTALLMENT = "installment"  # Versement sur créance
    INSTALLMENT_CANCELLED = "installment_cancelled"  # Versement annulé ce jour
    REFUND = "refund"  # Remboursement d'un retour

    @property
    def sign(self) -> int:
        return 1 if self in _INFLOWS else -1


_INFLOWS = frozenset({FlowKind.SALE_CASH, FlowKind.SALE_DEPOSIT, FlowKind.INSTALLMENT})


@dataclass(frozen=True, slots=True, kw_only=True)
class MoneyFlow:
    """Somme (positive) des mouvements d'une nature, d'un mode de paiement, d'une journée."""

    day: date
    kind: FlowKind
    mode_id: PaymentModeId
    amount: int
    count: int

    @property
    def signed(self) -> int:
        return self.kind.sign * self.amount


@dataclass(frozen=True, slots=True, kw_only=True)
class ExpenseFlow:
    """Dépenses d'une catégorie datées du jour (`cancelled=False`) ou annulées ce jour."""

    day: date
    category_id: ExpenseCategoryId
    amount: int
    count: int
    cancelled: bool

    @property
    def signed(self) -> int:
        return -self.amount if self.cancelled else self.amount


@dataclass(frozen=True, slots=True, kw_only=True)
class ReceivablesPosition:
    """Créances « En cours » maintenant : total à recevoir (§ 14.1) et clients débiteurs."""

    total_due: int
    debtor_count: int


@dataclass(frozen=True, slots=True, kw_only=True)
class PendingAlerts:
    """Alertes en attente du propriétaire (UC-TDB-01 point 6)."""

    error_reports: int
    """Signalements d'erreur de vente encore « Ouverts »."""
    price_requests: int
    """Demandes de prix sous le minimum en attente et non échues à `now`."""


class DashboardQueries(ShopBoundPort):
    """Agrégats en lecture seule ; listes triées par journée puis par clé (déterministes)."""

    @abstractmethod
    def sales_by_day(
        self, first_day: date, last_day: date, *, seller: UserId | None = None
    ) -> list[SalesDay]:
        """Ventes datées de la période, annulées comprises ; jours sans vente absents."""

    @abstractmethod
    def cancelled_by_day(
        self, first_day: date, last_day: date, *, seller: UserId | None = None
    ) -> list[SalesDay]:
        """Ventes annulées pendant la période, regroupées par journée d'annulation."""

    @abstractmethod
    def returns_by_day(
        self, first_day: date, last_day: date, *, seller: UserId | None = None
    ) -> list[ReturnsDay]:
        """Retours de la période (`returned_on`) ; `seller` : vendeur de la vente d'origine."""

    @abstractmethod
    def money_flows(self, first_day: date, last_day: date) -> list[MoneyFlow]:
        """Mouvements d'argent de la période, par journée, nature et mode."""

    @abstractmethod
    def expense_flows(self, first_day: date, last_day: date) -> list[ExpenseFlow]:
        """Dépenses de la période et annulations de la période, par journée et catégorie."""

    @abstractmethod
    def receivables_position(self, *, responsible: UserId | None = None) -> ReceivablesPosition:
        """Restes des créances En cours (initial - versements valides)."""

    @abstractmethod
    def reminders_due(self, today: date, *, responsible: UserId | None = None) -> int:
        """Rappels non faits datés au plus `today` sur des créances En cours (« du jour »,
        retards compris)."""

    @abstractmethod
    def pending_alerts(self, now: datetime) -> PendingAlerts: ...
