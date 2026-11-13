"""Ports du stock (T14) : projection, grand livre (ajout seul), ajustements, inventaires.

- `StockLevelRepository` : une ligne par article x lieu (`STOCK_LEVEL_KEY`, nom de la
  contrainte SQL) ; verrou optimiste par `version` (D6). Deux créations simultanées du même
  couple → `Duplicate` sur cette contrainte, rejouée comme un conflit de version.
- `StockMovementLog` : grand livre **en ajout seul** (ni `update` ni suppression, comme le
  journal) ; écrit uniquement par `StockLedger`, dans la transaction du document source.
- `InventoryRepository` : `INVENTORY_OPEN_LOCATION` = « un seul inventaire en cours par lieu »
  (clé `NULL` une fois validé ou abandonné, comme `alert_active_dedup`).
"""

from abc import abstractmethod
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from app.application.ports.aggregate import UniqueKey
from app.application.ports.errors import IsolationViolation
from app.application.ports.pagination import Cursor, Page, PageRequest
from app.application.ports.shop_bound import ShopBoundPort
from app.application.shops.ports import ShopRecordRepository
from app.domain.catalog.ids import ArticleId
from app.domain.shops.ids import LocationId
from app.domain.stock.adjustment import Adjustment
from app.domain.stock.ids import AdjustmentId, InventoryId, StockLevelId, StockMovementId
from app.domain.stock.inventory import Inventory
from app.domain.stock.level import StockLevel
from app.domain.stock.movement import StockMovement
from app.domain.stock.values import MovementType

STOCK_LEVEL_KEY = "stock_level_article_location"
INVENTORY_OPEN_LOCATION = "inventory_open_location"


def movement_position(movement: StockMovement) -> Cursor:
    """Ordre de l'historique (UC-STK-06) : date de l'opération puis identifiant, décroissants."""
    return Cursor(movement.occurred_at, movement.id.value)


class StockLevelRepository(ShopRecordRepository[StockLevelId, StockLevel]):
    def unique_keys(self) -> Sequence[UniqueKey[StockLevel]]:
        return (UniqueKey(STOCK_LEVEL_KEY, lambda level: level.key),)

    @abstractmethod
    def find_level(self, article_id: ArticleId, location_id: LocationId) -> StockLevel | None:
        """Projection du couple, ou `None` si aucun mouvement ne l'a encore créée."""

    @abstractmethod
    def for_article(self, article_id: ArticleId) -> list[StockLevel]:
        """Projections de l'article dans tous les lieux (ordre par identifiant)."""

    @abstractmethod
    def for_location(self, location_id: LocationId) -> list[StockLevel]:
        """Projections de tous les articles d'un lieu (ordre par identifiant)."""

    @abstractmethod
    def list_all(self) -> list[StockLevel]:
        """Toutes les projections de la boutique (matrice, valeur du stock, § 10)."""


class StockMovementLog(ShopBoundPort):
    """Grand livre de stock de la boutique, en ajout seul."""

    def append(self, movement: StockMovement) -> None:
        if movement.shop_id != self.shop_id:
            msg = "Mouvement de stock d'une autre boutique"
            raise IsolationViolation(msg)
        self._append(movement)

    @abstractmethod
    def find(self, movement_id: StockMovementId) -> StockMovement | None: ...

    @abstractmethod
    def reversal_of(self, movement_id: StockMovementId) -> StockMovement | None:
        """« Annulation » qui inverse ce mouvement, s'il y en a une."""

    @abstractmethod
    def for_source(self, source_id: UUID) -> list[StockMovement]:
        """Mouvements d'un document (achat, vente, ajustement…), du plus ancien au plus récent."""

    @abstractmethod
    def chronology(self, article_id: ArticleId) -> list[StockMovement]:
        """**Tous** les mouvements de l'article (tous lieux), par ordre d'enregistrement (`id`).

        Sert au Costing (T15) : rejeu du CMP (`replay_wac`) et contrôle « déjà sorti du lieu ».
        """

    @abstractmethod
    def for_article(self, article_id: ArticleId, page: PageRequest) -> Page[StockMovement]:
        """Historique de l'article, plus récent d'abord (`movement_position`)."""

    @abstractmethod
    def count_sources_since(
        self, location_id: LocationId, movement_type: MovementType, since: datetime
    ) -> int:
        """Documents distincts ayant posté `movement_type` au lieu, enregistrés depuis `since`."""

    @abstractmethod
    def _append(self, movement: StockMovement) -> None: ...


class AdjustmentRepository(ShopRecordRepository[AdjustmentId, Adjustment]):
    """Ajustements (créés, jamais modifiés : `add` seulement en pratique)."""


class InventoryRepository(ShopRecordRepository[InventoryId, Inventory]):
    def unique_keys(self) -> Sequence[UniqueKey[Inventory]]:
        return (UniqueKey(INVENTORY_OPEN_LOCATION, lambda inv: inv.open_location_key),)

    @abstractmethod
    def find_open(self, location_id: LocationId) -> Inventory | None:
        """Inventaire en cours du lieu, s'il y en a un."""

    @abstractmethod
    def started_since(self, since: datetime) -> list[Inventory]:
        """Inventaires lancés à partir de `since` (tous statuts), du plus ancien au plus récent
        (annulation d'un import : un inventaire qui compte un article du lot la bloque)."""
