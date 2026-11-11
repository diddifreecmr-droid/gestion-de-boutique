"""UC-VEN-11 — Gérer les clients (propriétaire : tous ; vendeur : « ses clients » ; CUS-01 à 03).

- Portée du vendeur **dans la requête** : clients qu'il a créés ou qui ont une vente de lui
  (Q-20) ; un autre client → 404. Comptable et chauffeur : 403 (RG-D03).
- Recherche par nom (plié) ou téléphone (chiffres) ; création idempotente par `customer_id` ;
  `PATCH` + `version`, avant/après au journal. Téléphone déjà pris dans la boutique → 409
  `DUPLICATE` (`field: phone` ; `existing_id` seulement si l'acteur voit ce client).
- Fiche : client, ventes (plus récentes d'abord ; pour un vendeur, les siennes seulement),
  total acheté (ventes valides) et total dû (restes à payer des ventes à crédit valides, en
  attendant les versements de T17). Photo de pièce d'identité : visible du propriétaire et
  du vendeur qui voit ce client (SEC-N06 ; URL signée avec T17 / TR-17).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWork, UnitOfWorkFactory
from app.application.sales.customer_input import customer_details, patched_details
from app.application.sales.ports import CustomerQuery, CustomerRepository, SaleRepository
from app.application.sales.resolver import require_visible
from app.application.sales.views import SaleView, view_of
from app.application.security.access import OwnScope
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop, performer_of, require_version
from app.domain.sales.customer import Customer, CustomerDetails
from app.domain.sales.ids import CustomerId
from app.domain.sales.values import SaleKind, SaleStatus
from app.domain.shared.errors import Duplicate
from app.domain.shared.ids import UserId
from app.domain.shared.money import Money


@dataclass(frozen=True, slots=True)
class CustomerSheet:
    customer: Customer
    sales: list[SaleView]
    total_bought: Money
    total_due: Money


class ManageCustomers:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock

    def _own(self, actor: Actor, permission: Permission) -> UserId | None:
        scope = self._policy.scope_filter(actor, permission)
        return scope.user_id if isinstance(scope, OwnScope) else None

    def search(self, actor: Actor, text: str | None = None) -> list[Customer]:
        seller = self._own(actor, Permission.CUSTOMER_READ)
        with self._uow_factory(actor_shop(actor)) as uow:
            return CustomerRepository.within(uow).search(CustomerQuery(text, seller))

    def sheet(self, actor: Actor, customer_id: CustomerId) -> CustomerSheet:
        seller = self._own(actor, Permission.CUSTOMER_READ)
        with self._uow_factory(actor_shop(actor)) as uow:
            customer = require_visible(uow, actor, customer_id)
            sales = SaleRepository.within(uow).for_customer(customer.id, seller=seller)
        valid = [sale for sale in sales if sale.status is SaleStatus.VALID]
        return CustomerSheet(
            customer=customer,
            sales=[view_of(self._policy, actor, sale) for sale in sales],
            total_bought=Money.total(sale.total for sale in valid),
            total_due=Money.total(s.remaining for s in valid if s.kind is SaleKind.CREDIT),
        )

    def create(
        self, actor: Actor, values: Mapping[str, Any], customer_id: CustomerId | None = None
    ) -> tuple[Customer, bool]:
        self._policy.require(actor, Permission.CUSTOMER_MANAGE)
        details = customer_details(values)
        with self._uow_factory(actor_shop(actor)) as uow:
            customers = CustomerRepository.within(uow)
            if customer_id is not None:
                existing = customers.find(customer_id)
                if existing is not None:
                    return require_visible(uow, actor, existing.id), False
            self._require_free_phone(uow, actor, details, None)
            customer = Customer.create(
                uow.shop_id,
                details,
                performer=performer_of(actor),
                now=self._clock.now(),
                customer_id=customer_id,
            )
            customers.add(customer)
            uow.commit()
        return customer, True

    def update(
        self, actor: Actor, customer_id: CustomerId, patch: Mapping[str, Any], version: int
    ) -> Customer:
        self._policy.require(actor, Permission.CUSTOMER_MANAGE)
        with self._uow_factory(actor_shop(actor)) as uow:
            customer = require_visible(uow, actor, customer_id)
            require_version(customer.version, version)
            details = patched_details(customer.details, patch)
            self._require_free_phone(uow, actor, details, customer.id)
            if customer.change(details, performer=performer_of(actor), now=self._clock.now()):
                CustomerRepository.within(uow).update(customer)
                uow.commit()
        return customer

    def _require_free_phone(
        self, uow: UnitOfWork, actor: Actor, details: CustomerDetails, own: CustomerId | None
    ) -> None:
        customers = CustomerRepository.within(uow)
        holder = customers.find_by_phone(details.phone)
        if holder is None or holder.id == own:
            return
        seller = self._own(actor, Permission.CUSTOMER_READ)
        visible = seller is None or customers.visible_to(holder.id, seller)
        found: dict[str, object] = {"field": "phone", "value": details.phone.e164}
        if visible:
            found["existing_id"] = str(holder.id)
        msg = "Ce téléphone est déjà celui d'un client"
        raise Duplicate(msg, details=found)
