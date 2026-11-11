"""UC-STK-07 — Valider un inventaire (INV-03, INV-04, INV-06).

1. Toutes les lignes comptées ; `version` lue (409 sinon).
2. Théorique = stock **vendable** du lieu **au moment de la validation** (Q-17) ; écart =
   compté - théorique ; valeur = écart x CMP (« non calculable » si le CMP est inconnu).
3. Motif obligatoire pour chaque écart non nul, ou motif global (`ReasonRequired`, 400, qui
   liste les articles concernés **sans** révéler le théorique).
4. Chaque écart crée un ajustement (motif « écart d'inventaire », document lié : l'inventaire)
   et son mouvement ; le propriétaire reçoit une alerte avec la valeur totale des écarts.

Toute la validation est **une** transaction, rejouée sur conflit de concurrence (une vente
pendant la validation change le théorique : le rejeu le relit).
"""

from collections.abc import Mapping

from app.application.catalog.ports import ArticleRepository
from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWorkFactory
from app.application.security.actor import Actor
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop, performer_of, require_version
from app.application.stock.adjusting import post_adjustment
from app.application.stock.ledger import StockLedger
from app.application.stock.ports import InventoryRepository, StockLevelRepository
from app.application.stock.retry import with_stock_retry
from app.application.stock.use_cases.inventories import PERMISSION, InventorySheet, inventory_sheet
from app.application.stock.visibility import stock_visibility
from app.domain.catalog.ids import ArticleId
from app.domain.shared.quantity import Quantity
from app.domain.stock.adjustment import AdjustmentDirection, AdjustmentDraft, AdjustmentReason
from app.domain.stock.ids import InventoryId
from app.domain.stock.inventory import Inventory
from app.domain.stock.inventory_line import LineCheck
from app.domain.stock.values import StockCondition


class ValidateInventory:
    def __init__(
        self, uow_factory: UnitOfWorkFactory, policy: Policy, ledger: StockLedger, clock: Clock
    ) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._ledger = ledger
        self._clock = clock

    def execute(
        self,
        actor: Actor,
        inventory_id: InventoryId,
        version: int,
        *,
        reasons: Mapping[ArticleId, str] | None = None,
        global_reason: str | None = None,
    ) -> InventorySheet:
        self._policy.require(actor, PERMISSION)
        inventory = with_stock_retry(
            lambda: self._attempt(actor, inventory_id, version, reasons or {}, global_reason)
        )
        with self._uow_factory(actor_shop(actor)) as uow:
            return inventory_sheet(uow, inventory, stock_visibility(self._policy, actor))

    def _attempt(
        self,
        actor: Actor,
        inventory_id: InventoryId,
        version: int,
        reasons: Mapping[ArticleId, str],
        global_reason: str | None,
    ) -> Inventory:
        performer, now = performer_of(actor), self._clock.now()
        with self._uow_factory(actor_shop(actor)) as uow:
            inventories = InventoryRepository.within(uow)
            inventory = inventories.get(inventory_id)
            require_version(inventory.version, version)
            levels = StockLevelRepository.within(uow)
            articles = ArticleRepository.within(uow)
            checks = {}
            for article_id, line in inventory.lines.items():
                level = levels.find_level(article_id, inventory.location_id)
                theoretical = Quantity.zero(line.unit) if level is None else level.sellable
                checks[article_id] = LineCheck(theoretical, articles.get(article_id).wac)
            gaps = inventory.validate(
                checks, reasons=reasons, global_reason=global_reason, performer=performer, now=now
            )
            inventories.update(inventory)
            for line in gaps:
                difference = line.difference
                if difference is None:  # exclu par `validate` : toute ligne en écart est comptée
                    msg = "Écart sans quantité comptée"
                    raise RuntimeError(msg)
                entering = difference.value > 0
                draft = AdjustmentDraft(
                    location_id=inventory.location_id,
                    article_id=line.article_id,
                    direction=AdjustmentDirection.IN if entering else AdjustmentDirection.OUT,
                    quantity=difference if entering else -difference,
                    condition=StockCondition.SELLABLE,
                    reason=AdjustmentReason.INVENTORY_GAP,
                    note=line.reason,
                    inventory_id=inventory.id,
                )
                post_adjustment(
                    uow,
                    self._ledger,
                    draft,
                    performer=performer,
                    now=now,
                    inventory_number=inventory.number,
                )
            uow.commit()
        return inventory
