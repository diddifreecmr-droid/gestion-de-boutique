"""Identifiants typés du stock (UUIDv7, specs D5)."""

from app.domain.shared.ids import EntityId


class StockMovementId(EntityId):
    """Ligne du grand livre de stock (immuable)."""

    __slots__ = ()


class StockLevelId(EntityId):
    """Projection article x lieu (`stock_level`)."""

    __slots__ = ()


class AdjustmentId(EntityId):
    """Ajustement ponctuel ou écart d'inventaire (UC-STK-08)."""

    __slots__ = ()


class InventoryId(EntityId):
    """Inventaire d'un lieu (UC-STK-07)."""

    __slots__ = ()
