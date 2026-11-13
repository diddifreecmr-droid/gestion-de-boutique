"""Droits du retour et de l'échange (UC-VEN-09, UC-PAP-01, décision client QC-4, T29).

- **Retour simple** : `SALE_RETURN` (propriétaire seul).
- **Échange** : `SALE_EXCHANGE`. Propriétaire (`ALL`) : toujours, toute vente, délai
  dépassable (échange « hors délai » inscrit au journal comme action sensible). Vendeur (`OWN`) :
  seulement si le réglage `employee_exchange_allowed` est vrai (sinon 403 `FORBIDDEN`,
  `details.setting`), seulement **ses** ventes (vente d'un autre → 404, comme `GetSale`) et
  seulement dans le délai `exchange_days` (sinon 422 `EXCHANGE_PERIOD_OVER`).

Ordre (`RecordReturn`) : permission avant toute lecture → réglage et propriété de la vente
avant le rejeu idempotent (un rejeu ne révèle rien d'autrui) → délai après le rejeu (un rejeu
d'un échange déjà fait reste 200 même si le délai est passé depuis).
"""

from datetime import date

from app.application.ports.repository import not_found
from app.application.ports.uow import UnitOfWork
from app.application.security.access import Access
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.ports import ShopSettingsRepository
from app.domain.sales.exchange_period import check_exchange_period
from app.domain.sales.sale import Sale
from app.domain.sales.sale_return import SaleReturn
from app.domain.shared.errors import Forbidden

SETTING = "employee_exchange_allowed"


class EmployeeExchangeDisabled(Forbidden):
    """Vendeur, réglage `employee_exchange_allowed` faux (défaut) → 403 `FORBIDDEN`."""

    def __init__(self) -> None:
        super().__init__(
            "L'échange par l'employé n'est pas autorisé dans cette boutique",
            details={"permission": Permission.SALE_EXCHANGE.value, "setting": SETTING},
        )


def required_access(policy: Policy, actor: Actor, *, exchange: bool) -> Access:
    """Permission du retour (`SALE_RETURN`) ou de l'échange (`SALE_EXCHANGE`) ; lève sinon."""
    permission = Permission.SALE_EXCHANGE if exchange else Permission.SALE_RETURN
    access = policy.require(actor, permission)
    if access not in (Access.ALL, Access.OWN):
        msg = f"Accès inattendu {access} pour {permission}"
        raise RuntimeError(msg)
    return access


def require_own_exchange(uow: UnitOfWork, actor: Actor, access: Access, sale: Sale) -> None:
    """Vendeur : réglage actif (403) puis sa propre vente (404). Rien pour le propriétaire."""
    if access is not Access.OWN:
        return
    if not ShopSettingsRepository.within(uow).current().values.employee_exchange_allowed:
        raise EmployeeExchangeDisabled
    if sale.seller_id != actor.user_id:
        raise not_found(sale.id)


def require_same_sale(access: Access, existing: SaleReturn, sale: Sale) -> None:
    """Rejeu idempotent par un vendeur : le retour doit appartenir à la vente citée (404)."""
    if access is Access.OWN and existing.sale_id != sale.id:
        raise not_found(existing.id)


def exchange_is_late(uow: UnitOfWork, access: Access, sale: Sale, today: date) -> bool:
    """Délai `exchange_days` : vendeur hors délai → 422 ; propriétaire → `True` (journal)."""
    days = ShopSettingsRepository.within(uow).current().values.exchange_days
    return check_exchange_period(sale.content.sold_on, today, days, may_exceed=access is Access.ALL)
