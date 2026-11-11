"""UC-STK-07 — Lancer et consulter un inventaire (comptable, propriétaire ; INV-01, INV-05, INV-06).

- Lancement : lieu actif ; un seul inventaire en cours par lieu (`INVENTORY_IN_PROGRESS`, 422,
  y compris sous course : la contrainte `inventory_open_location` tranche) ; numéro
  `INV-000001` ; une ligne par article **actif** du catalogue. Idempotent par `inventory_id`.
- Consultation (`InventorySheet`) : noms des articles et du lieu, et le nombre de **ventes
  enregistrées depuis le début du comptage** au lieu (documents « Sortie vente » distincts du
  grand livre). Tant que l'inventaire est en cours, la quantité théorique n'existe pas dans
  l'agrégat : elle ne peut pas être renvoyée (INV-01).
"""

from dataclasses import dataclass

from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWork, UnitOfWorkFactory
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop, performer_of
from app.application.shops.ports import LocationRepository
from app.application.stock.ports import (
    INVENTORY_OPEN_LOCATION,
    InventoryRepository,
    StockMovementLog,
)
from app.application.stock.reading import all_articles
from app.application.stock.visibility import StockVisibility, stock_visibility
from app.domain.catalog.details import ArticleStatus
from app.domain.catalog.ids import ArticleId
from app.domain.shared.doc_number import DocType
from app.domain.shared.errors import Duplicate, ValidationFailed
from app.domain.shops.ids import LocationId
from app.domain.stock.errors import InventoryAlreadyOpen
from app.domain.stock.ids import InventoryId
from app.domain.stock.inventory import Inventory, InventoryStatus
from app.domain.stock.values import MovementType

PERMISSION = Permission.INVENTORY_MANAGE


@dataclass(frozen=True, slots=True, kw_only=True)
class InventorySheet:
    inventory: Inventory
    location_name: str
    article_names: dict[ArticleId, str]
    sales_since_start: int
    visibility: StockVisibility


def inventory_sheet(
    uow: UnitOfWork, inventory: Inventory, visibility: StockVisibility
) -> InventorySheet:
    location = LocationRepository.within(uow).get(inventory.location_id)
    names = {article.id: article.display_name for article in all_articles(uow)}
    sales = 0
    if inventory.status is InventoryStatus.IN_PROGRESS:
        sales = StockMovementLog.within(uow).count_sources_since(
            inventory.location_id, MovementType.SALE_OUT, inventory.started_at
        )
    return InventorySheet(
        inventory=inventory,
        location_name=location.name,
        article_names={aid: names.get(aid, "?") for aid in inventory.lines},
        sales_since_start=sales,
        visibility=visibility,
    )


class StartInventory:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock

    def execute(
        self, actor: Actor, location_id: LocationId, inventory_id: InventoryId | None = None
    ) -> tuple[InventorySheet, bool]:
        self._policy.require(actor, PERMISSION)
        visibility = stock_visibility(self._policy, actor)
        try:
            return self._start(actor, location_id, inventory_id, visibility)
        except Duplicate as exc:
            if exc.details.get("constraint") != INVENTORY_OPEN_LOCATION:
                raise
            raise InventoryAlreadyOpen(str(location_id)) from exc

    def _start(
        self,
        actor: Actor,
        location_id: LocationId,
        inventory_id: InventoryId | None,
        visibility: StockVisibility,
    ) -> tuple[InventorySheet, bool]:
        with self._uow_factory(actor_shop(actor)) as uow:
            inventories = InventoryRepository.within(uow)
            existing = None if inventory_id is None else inventories.find(inventory_id)
            if existing is not None:
                return inventory_sheet(uow, existing, visibility), False
            location = LocationRepository.within(uow).get(location_id)
            if not location.active:
                msg = "Ce lieu est désactivé"
                raise ValidationFailed(msg, details={"field": "location_id"})
            running = inventories.find_open(location.id)
            if running is not None:
                raise InventoryAlreadyOpen(str(location.id), str(running.id))
            articles = all_articles(uow, status=ArticleStatus.ACTIVE)
            inventory = Inventory.start(
                shop_id=uow.shop_id,
                number=uow.numbering.next(DocType.INVENTORY),
                location_id=location.id,
                articles=[(a.id, a.details.fields.stock_unit) for a in articles],
                performer=performer_of(actor),
                now=self._clock.now(),
                inventory_id=inventory_id,
            )
            inventories.add(inventory)
            uow.commit()
        with self._uow_factory(actor_shop(actor)) as uow:
            return inventory_sheet(uow, inventory, visibility), True


class GetInventory:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy) -> None:
        self._uow_factory = uow_factory
        self._policy = policy

    def execute(self, actor: Actor, inventory_id: InventoryId) -> InventorySheet:
        self._policy.require(actor, PERMISSION)
        visibility = stock_visibility(self._policy, actor)
        with self._uow_factory(actor_shop(actor)) as uow:
            inventory = InventoryRepository.within(uow).get(inventory_id)
            return inventory_sheet(uow, inventory, visibility)
