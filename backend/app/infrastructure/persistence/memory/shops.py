"""Dépôts mémoire du socle des boutiques (gabarit `MemoryRepository` + listes).

Les noms de table servent aussi aux lectures plateforme (`memory/directories.py`).
"""

import copy
from collections.abc import Callable
from datetime import datetime
from typing import Any, cast

from app.application.ports.aggregate import Aggregate
from app.application.ports.repository import not_found
from app.application.shops.ports import (
    AdminGrantRepository,
    ExpenseCategoryRepository,
    LocationRepository,
    MembershipRepository,
    PaymentModeRepository,
    ShopRepository,
    ShopSettingsRepository,
)
from app.domain.shared.ids import EntityId, ShopId, UserId
from app.domain.shops.admin_grant import AdminAccessGrant
from app.domain.shops.expense_category import ExpenseCategory
from app.domain.shops.ids import (
    AdminGrantId,
    ExpenseCategoryId,
    LocationId,
    MembershipId,
    PaymentModeId,
    ShopSettingsId,
)
from app.domain.shops.location import Location
from app.domain.shops.membership import Membership
from app.domain.shops.payment_mode import PaymentMode
from app.domain.shops.settings import ShopSettings
from app.domain.shops.shop import Shop
from app.infrastructure.persistence.memory.census import MemoryShopDataCensus
from app.infrastructure.persistence.memory.repository import MemoryRepository

SHOPS_TABLE = "shops"
MEMBERSHIPS_TABLE = "memberships"
ADMIN_GRANTS_TABLE = "admin_access_grants"


class _Listing[IdT: EntityId, AggT: Aggregate](MemoryRepository[IdT, AggT]):
    def _sorted(self, key: Callable[[AggT], Any]) -> list[AggT]:
        # Les lignes de cette table ne sont construites que par `_row` à partir d'un AggT.
        rows = self._transaction.rows(self.table)
        aggregates = [cast(AggT, copy.deepcopy(row.payload)) for row in rows]
        for aggregate in aggregates:
            self._tracker.track(aggregate, saved=False)
        return sorted(aggregates, key=key)


class MemoryShopRepository(_Listing[ShopId, Shop], ShopRepository):
    table = SHOPS_TABLE


class MemoryShopSettingsRepository(_Listing[ShopSettingsId, ShopSettings], ShopSettingsRepository):
    table = "shop_settings"

    def current(self) -> ShopSettings:
        found = self._sorted(key=lambda settings: settings.id)
        if not found:
            raise not_found(self.shop_id)
        return found[0]


class MemoryLocationRepository(_Listing[LocationId, Location], LocationRepository):
    table = "locations"

    def list_all(self) -> list[Location]:
        return self._sorted(key=lambda loc: (loc.details.display_order, loc.name_key, loc.id))


class MemoryPaymentModeRepository(_Listing[PaymentModeId, PaymentMode], PaymentModeRepository):
    table = "payment_modes"

    def list_all(self) -> list[PaymentMode]:
        return self._sorted(key=lambda mode: (mode.details.display_order, mode.name_key, mode.id))


class MemoryExpenseCategoryRepository(
    _Listing[ExpenseCategoryId, ExpenseCategory], ExpenseCategoryRepository
):
    table = "expense_categories"

    def list_all(self) -> list[ExpenseCategory]:
        return self._sorted(key=lambda cat: (cat.display_order, cat.name_key, cat.id))


class MemoryMembershipRepository(_Listing[MembershipId, Membership], MembershipRepository):
    table = MEMBERSHIPS_TABLE

    def find_by_user(self, user_id: UserId) -> Membership | None:
        found = [m for m in self._sorted(key=lambda m: m.id) if m.user_id == user_id]
        return found[0] if found else None

    def list_all(self) -> list[Membership]:
        return self._sorted(key=lambda membership: membership.id)


class MemoryAdminGrantRepository(_Listing[AdminGrantId, AdminAccessGrant], AdminGrantRepository):
    table = ADMIN_GRANTS_TABLE

    def active(self, now: datetime) -> AdminAccessGrant | None:
        running = [g for g in self._sorted(key=lambda g: g.granted_at) if g.is_active(now)]
        return running[-1] if running else None


SHOP_REPOSITORIES = (
    MemoryShopRepository,
    MemoryShopSettingsRepository,
    MemoryLocationRepository,
    MemoryPaymentModeRepository,
    MemoryExpenseCategoryRepository,
    MemoryMembershipRepository,
    MemoryAdminGrantRepository,
    MemoryShopDataCensus,
)
