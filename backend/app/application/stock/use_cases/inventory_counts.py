"""UC-STK-07 — Saisir les quantités comptées, abandonner un inventaire (INV-02).

- Comptage **partiel et cumulatif** : chaque envoi complète les précédents (une quantité
  `None` efface un comptage) ; reprise plus tard sans perte. Quantité ≥ 0 dans l'unité de
  stock de l'article (1,5 moto → 400). `version` lue obligatoire (409 sinon).
- Abandon : l'inventaire passe « Abandonné », aucun ajustement ; le lieu peut en relancer un.
"""

from collections.abc import Mapping
from decimal import Decimal

from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWorkFactory
from app.application.security.actor import Actor
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop, performer_of, require_version
from app.application.stock.ports import InventoryRepository
from app.application.stock.use_cases.inventories import PERMISSION, InventorySheet, inventory_sheet
from app.application.stock.visibility import stock_visibility
from app.domain.catalog.ids import ArticleId
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.quantity import Quantity
from app.domain.stock.ids import InventoryId

type Counts = Mapping[ArticleId, Decimal | str | None]


class RecordCounts:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock

    def execute(
        self, actor: Actor, inventory_id: InventoryId, counts: Counts, version: int
    ) -> InventorySheet:
        self._policy.require(actor, PERMISSION)
        visibility = stock_visibility(self._policy, actor)
        with self._uow_factory(actor_shop(actor)) as uow:
            inventories = InventoryRepository.within(uow)
            inventory = inventories.get(inventory_id)
            require_version(inventory.version, version)
            unknown = sorted(str(aid) for aid in counts if aid not in inventory.lines)
            if unknown:
                msg = "Article absent de cet inventaire"
                raise ValidationFailed(msg, details={"field": "counts", "articles": unknown})
            quantities = {
                aid: None if value is None else Quantity.of(value, inventory.lines[aid].unit)
                for aid, value in counts.items()
            }
            inventory.record_counts(
                quantities, performer=performer_of(actor), now=self._clock.now()
            )
            inventories.update(inventory)
            uow.commit()
        with self._uow_factory(actor_shop(actor)) as uow:
            return inventory_sheet(uow, inventory, visibility)


class AbandonInventory:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock

    def execute(self, actor: Actor, inventory_id: InventoryId, version: int) -> InventorySheet:
        self._policy.require(actor, PERMISSION)
        visibility = stock_visibility(self._policy, actor)
        with self._uow_factory(actor_shop(actor)) as uow:
            inventories = InventoryRepository.within(uow)
            inventory = inventories.get(inventory_id)
            require_version(inventory.version, version)
            inventory.abandon(performer=performer_of(actor), now=self._clock.now())
            inventories.update(inventory)
            uow.commit()
        with self._uow_factory(actor_shop(actor)) as uow:
            return inventory_sheet(uow, inventory, visibility)
