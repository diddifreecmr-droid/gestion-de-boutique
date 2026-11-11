"""Contrôles de la vente qui dépendent du rôle : prix minimum (H9) et plafond de crédit.

- **Prix minimum** (UC-VEN-03, ERR-PRM-01 à 04) : réglage actif et prix vendu **strictement**
  sous le minimum de l'article. Vendeur → `PRICE_BELOW_MINIMUM` (`request_required: true`) ;
  une demande acceptée le débloque (`price_approval.py`, T16b).
  Propriétaire → accepté, journal « sensible » (`SaleRecordedBelowMinimum`).
- **Plafond de crédit (Q-45 tranchée)** : dette après la vente = dû actuel + reste de cette
  vente ; « dépasser » est **strict** (égalité acceptée, ERR-CRD-02). Vendeur → refus
  `CREDIT_LIMIT_EXCEEDED` ; propriétaire → vente acceptée avec l'avertissement
  `{code, message, details}` dans `warnings` (ERR-CRD-03), sans confirmation à renvoyer.
- **Dû actuel du client** : en attendant les créances (T17), somme des restes à payer de ses
  ventes à crédit valides ; T17 y retranchera les versements (port `CustomerDebt`).
"""

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass, field

from app.application.ports.uow import UnitOfWork
from app.application.sales.lines import minimum_of
from app.application.sales.ports import SaleRepository
from app.application.security.actor import Actor
from app.application.security.roles import Role
from app.domain.catalog.article import Article
from app.domain.sales.customer import Customer
from app.domain.sales.errors import CreditLimitExceeded, PriceBelowMinimum
from app.domain.sales.ids import CustomerId
from app.domain.sales.lines import SaleLine
from app.domain.sales.values import SaleKind, SaleStatus
from app.domain.shared.money import Money


@dataclass(frozen=True, slots=True)
class SaleWarning:
    """Avertissement accepté (propriétaire) : même code que l'erreur qu'il remplace."""

    code: str
    message: str
    details: dict[str, object] = field(default_factory=dict)


class CustomerDebt(ABC):
    """Dû actuel d'un client (« Total dû », CDC § 20.4) : servi par T17 une fois livré."""

    @abstractmethod
    def due(self, uow: UnitOfWork, customer_id: CustomerId) -> Money: ...


class SalesCustomerDebt(CustomerDebt):
    """Lot 1 avant T17 : restes à payer des ventes à crédit valides (sans versements)."""

    def due(self, uow: UnitOfWork, customer_id: CustomerId) -> Money:
        sales = SaleRepository.within(uow).for_customer(customer_id)
        return Money.total(
            sale.remaining
            for sale in sales
            if sale.kind is SaleKind.CREDIT and sale.status is SaleStatus.VALID
        )


def check_minimums(
    lines: Iterable[tuple[SaleLine, Article]], *, enabled: bool, actor: Actor
) -> bool:
    """Vrai si une ligne est sous le minimum (propriétaire) ; lève pour tout autre rôle."""
    below = False
    for position, (line, article) in enumerate(lines, start=1):
        minimum = minimum_of(article, line, enabled=enabled)
        if minimum is None or line.unit_price >= minimum:
            continue
        if actor.role is not Role.OWNER:
            raise PriceBelowMinimum(article_id=str(article.id), line=position, min_price=minimum)
        below = True
    return below


def check_credit_limit(
    uow: UnitOfWork, debt: CustomerDebt, actor: Actor, customer: Customer, remaining: Money
) -> list[SaleWarning]:
    limit = customer.details.credit_limit
    if limit is None:
        return []
    due = debt.due(uow, customer.id)
    if due + remaining <= limit:
        return []
    error = CreditLimitExceeded(
        customer_id=str(customer.id), limit=limit, due_before=due, due_after=due + remaining
    )
    if actor.role is not Role.OWNER:
        raise error
    return [SaleWarning(error.code, error.message, dict(error.details))]
