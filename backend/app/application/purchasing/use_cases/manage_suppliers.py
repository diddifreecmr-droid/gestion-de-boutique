"""UC-ACH-02 — Gérer les fournisseurs (comptable, propriétaire ; recette SUP-01, SUP-02).

- Liste (`SUPPLIER_READ`), création idempotente par `supplier_id` client, modification
  `PATCH` + `version` (`SUPPLIER_MANAGE`) ; nom en double → `409 DUPLICATE` (`supplier_name`).
- Aucune suppression : un fournisseur se **désactive** (`active: false`), achats ou non.
- Fiche : fournisseur, achats de la période (date décroissante) et total acheté (achats
  valides seulement, RG-T03) ; période par défaut : du 1er du mois à aujourd'hui.
"""

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import date
from typing import Any

from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWorkFactory
from app.application.purchasing.ports import PurchaseRepository, SupplierRepository
from app.application.purchasing.use_cases.read_purchases import (
    PurchaseCriteria,
    PurchaseTotals,
    find_purchases,
    period_of,
    totals_of,
)
from app.application.purchasing.views import PurchaseView, view_of
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop, performer_of, require_version
from app.domain.purchasing.ids import SupplierId
from app.domain.purchasing.supplier import Supplier, SupplierDetails

PATCHABLE = frozenset({"name", "phone", "city", "country", "note", "active"})


@dataclass(frozen=True, slots=True)
class SupplierSheet:
    supplier: Supplier
    purchases: list[PurchaseView]
    totals: PurchaseTotals
    first_day: date
    last_day: date


class ManageSuppliers:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock

    def list_all(self, actor: Actor) -> list[Supplier]:
        self._policy.require(actor, Permission.SUPPLIER_READ)
        with self._uow_factory(actor_shop(actor)) as uow:
            return SupplierRepository.within(uow).list_all()

    def create(
        self, actor: Actor, details: SupplierDetails, supplier_id: SupplierId | None = None
    ) -> tuple[Supplier, bool]:
        self._policy.require(actor, Permission.SUPPLIER_MANAGE)
        now = self._clock.now()
        with self._uow_factory(actor_shop(actor)) as uow:
            suppliers = SupplierRepository.within(uow)
            if supplier_id is not None:
                existing = suppliers.find(supplier_id)
                if existing is not None:
                    return existing, False
            supplier = Supplier.create(
                uow.shop_id,
                details,
                performer=performer_of(actor),
                now=now,
                supplier_id=supplier_id,
            )
            suppliers.add(supplier)
            uow.commit()
        return supplier, True

    def update(
        self, actor: Actor, supplier_id: SupplierId, patch: Mapping[str, Any], version: int
    ) -> Supplier:
        unknown = set(patch) - PATCHABLE
        if unknown:
            msg = f"Champs non modifiables : {sorted(unknown)}"
            raise ValueError(msg)
        self._policy.require(actor, Permission.SUPPLIER_MANAGE)
        now = self._clock.now()
        with self._uow_factory(actor_shop(actor)) as uow:
            suppliers = SupplierRepository.within(uow)
            supplier = suppliers.get(supplier_id)
            require_version(supplier.version, version)
            details = SupplierDetails(**(asdict(supplier.details) | dict(patch)))
            if supplier.change(details, performer=performer_of(actor), now=now):
                suppliers.update(supplier)
                uow.commit()
        return supplier

    def sheet(
        self,
        actor: Actor,
        supplier_id: SupplierId,
        first_day: date | None = None,
        last_day: date | None = None,
    ) -> SupplierSheet:
        self._policy.require(actor, Permission.SUPPLIER_READ)
        self._policy.require(actor, Permission.PURCHASE_READ)
        today = self._clock.today()
        first, last = period_of(first_day, last_day, today)
        with self._uow_factory(actor_shop(actor)) as uow:
            supplier = SupplierRepository.within(uow).get(supplier_id)
            criteria = PurchaseCriteria(supplier_id=supplier.id)
            found = find_purchases(PurchaseRepository.within(uow), criteria, first, last)
        views = [view_of(actor, purchase, today) for purchase in found]
        return SupplierSheet(supplier, views, totals_of(found), first, last)
