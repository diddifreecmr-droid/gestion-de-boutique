"""Lectures **plateforme** mémoire, sur l'état validé : rattachements, boutiques, délégations.

Elles traversent les boutiques (`MemoryDatabase.all_rows`) : elles ne servent qu'à
l'authentification (rôle relu à chaque requête), au journal de l'identité et à la console de
l'administrateur, jamais à un dépôt de boutique.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import cast

from app.application.identity.ports import (
    AdminDelegationDirectory,
    MembershipDirectory,
    MembershipView,
)
from app.application.shops.ports import ShopCatalog, ShopSummary
from app.domain.shared.ids import ShopId, UserId
from app.domain.shops.account import MerchantAccount
from app.domain.shops.admin_grant import AdminAccessGrant
from app.domain.shops.membership import Membership
from app.domain.shops.shop import Shop
from app.domain.shops.values import ShopStatus
from app.infrastructure.persistence.memory.database import MemoryDatabase
from app.infrastructure.persistence.memory.platform_repositories import (
    MemoryMerchantAccountRepository,
)
from app.infrastructure.persistence.memory.platform_store import MemoryPlatformStore
from app.infrastructure.persistence.memory.shops import (
    ADMIN_GRANTS_TABLE,
    MEMBERSHIPS_TABLE,
    SHOPS_TABLE,
)


def _shops(database: MemoryDatabase) -> dict[ShopId, Shop]:
    # Lignes construites par `MemoryShopRepository._row` à partir d'un `Shop`.
    return {row.shop_id: cast(Shop, row.payload) for row in database.all_rows(SHOPS_TABLE)}


class MemoryMembershipDirectory(MembershipDirectory):
    def __init__(self, database: MemoryDatabase) -> None:
        self._database = database

    def for_user(self, user_id: UserId) -> Sequence[MembershipView]:
        shops = _shops(self._database)
        views = [
            self._view(membership, shops[membership.shop_id])
            for membership in self._memberships()
            if membership.user_id == user_id
        ]
        return sorted(views, key=lambda view: (view.shop_name, view.shop_id))

    def find(self, user_id: UserId, shop_id: ShopId) -> MembershipView | None:
        shop = _shops(self._database).get(shop_id)
        for membership in self._memberships():
            if membership.user_id == user_id and membership.shop_id == shop_id:
                if shop is None:  # rattachement sans boutique : base incohérente
                    msg = f"Rattachement à une boutique absente : {shop_id}"
                    raise RuntimeError(msg)
                return self._view(membership, shop)
        return None

    def _memberships(self) -> list[Membership]:
        rows = self._database.all_rows(MEMBERSHIPS_TABLE)
        return [cast(Membership, row.payload) for row in rows]

    @staticmethod
    def _view(membership: Membership, shop: Shop) -> MembershipView:
        return MembershipView(
            shop_id=shop.id,
            shop_name=shop.name,
            role=membership.role,
            active=membership.active,
            shop_active=shop.status is ShopStatus.ACTIVE,
        )


class MemoryShopCatalog(ShopCatalog):
    def __init__(self, database: MemoryDatabase, store: MemoryPlatformStore) -> None:
        self._database = database
        self._store = store

    def list_all(self) -> Sequence[ShopSummary]:
        accounts = self._accounts()
        summaries = [self._summary(shop, accounts) for shop in _shops(self._database).values()]
        return sorted(summaries, key=lambda summary: (summary.name, summary.shop_id))

    def find(self, shop_id: ShopId) -> ShopSummary | None:
        shop = _shops(self._database).get(shop_id)
        return None if shop is None else self._summary(shop, self._accounts())

    def _accounts(self) -> dict[object, MerchantAccount]:
        rows = self._store.rows(MemoryMerchantAccountRepository.table)
        return {key: cast(MerchantAccount, row.payload) for key, row in rows.items()}

    @staticmethod
    def _summary(shop: Shop, accounts: dict[object, MerchantAccount]) -> ShopSummary:
        account = accounts[shop.account_id]  # KeyError : boutique sans compte, base incohérente
        return ShopSummary(
            shop_id=shop.id,
            name=shop.name,
            profile_code=shop.profile_code,
            city=shop.identity.city,
            status=shop.status,
            enabled_modules=shop.enabled_modules,
            account_id=account.id,
            account_name=account.name,
            plan=account.plan,
            created_at=shop.created_at,
        )


class MemoryAdminDelegations(AdminDelegationDirectory):
    def __init__(self, database: MemoryDatabase) -> None:
        self._database = database

    def active_until(self, shop_id: ShopId, now: datetime) -> datetime | None:
        rows = self._database.rows(ADMIN_GRANTS_TABLE, shop_id).values()
        grants = [cast(AdminAccessGrant, row.payload) for row in rows]
        running = [grant.expires_at for grant in grants if grant.is_active(now)]
        return max(running) if running else None
