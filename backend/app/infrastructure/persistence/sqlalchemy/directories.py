"""Lectures **plateforme** SQL, sur l'état validé (connexion courte du pool) : rattachements,
boutiques de la console, délégations de l'administrateur. Pendant de `memory/directories.py`.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Any

import sqlalchemy as sa

from app.application.identity.ports import (
    AdminDelegationDirectory,
    MembershipDirectory,
    MembershipView,
)
from app.application.shops.ports import ShopCatalog, ShopSummary
from app.domain.plans.entitlements import PlanCode
from app.domain.shared.ids import ShopId, UserId
from app.domain.shared.roles import Role
from app.domain.shops.ids import MerchantAccountId
from app.domain.shops.values import ShopStatus
from app.infrastructure.persistence.sqlalchemy import tables_shops as t
from app.infrastructure.persistence.sqlalchemy.columns import from_db, to_db
from app.infrastructure.persistence.sqlalchemy.shops import shop_from_row
from app.infrastructure.persistence.sqlalchemy.tables_identity import merchant_account


class _Reader:
    def __init__(self, engine: sa.Engine) -> None:
        self._engine = engine

    def _rows(self, statement: sa.Select[Any]) -> list[sa.RowMapping]:
        with self._engine.connect() as connection:
            return list(connection.execute(statement).mappings().all())


class SqlMembershipDirectory(_Reader, MembershipDirectory):
    def _select(self, *conditions: sa.ColumnElement[bool]) -> list[MembershipView]:
        m, s = t.membership.c, t.shop.c
        statement = (
            sa.select(m.shop_id, m.role, m.active, s.name, s.status)
            .select_from(t.membership.join(t.shop, s.id == m.shop_id))
            .where(*conditions)
            .order_by(s.name, m.shop_id)
        )
        return [
            MembershipView(
                shop_id=ShopId(row["shop_id"]),
                shop_name=row["name"],
                role=Role(row["role"]),
                active=bool(row["active"]),
                shop_active=row["status"] == ShopStatus.ACTIVE.value,
            )
            for row in self._rows(statement)
        ]

    def for_user(self, user_id: UserId) -> Sequence[MembershipView]:
        return self._select(t.membership.c.user_id == user_id.value)

    def find(self, user_id: UserId, shop_id: ShopId) -> MembershipView | None:
        c = t.membership.c
        found = self._select(c.user_id == user_id.value, c.shop_id == shop_id.value)
        return found[0] if found else None


class SqlShopCatalog(_Reader, ShopCatalog):
    def _select(self, *conditions: sa.ColumnElement[bool]) -> list[ShopSummary]:
        s, a = t.shop.c, merchant_account.c
        statement = (
            sa.select(t.shop, a.name.label("account_name"), a.plan)
            .select_from(t.shop.join(merchant_account, a.id == s.account_id))
            .where(*conditions)
            .order_by(s.name, s.id)
        )
        summaries = []
        for row in self._rows(statement):
            shop = shop_from_row(row, version=int(row["version"]))
            summaries.append(
                ShopSummary(
                    shop_id=shop.id,
                    name=shop.name,
                    profile_code=shop.profile_code,
                    city=shop.identity.city,
                    status=shop.status,
                    enabled_modules=shop.enabled_modules,
                    account_id=MerchantAccountId(row["account_id"]),
                    account_name=row["account_name"],
                    plan=PlanCode(row["plan"]),
                    created_at=shop.created_at,
                )
            )
        return summaries

    def list_all(self) -> Sequence[ShopSummary]:
        return self._select()

    def find(self, shop_id: ShopId) -> ShopSummary | None:
        found = self._select(t.shop.c.id == shop_id.value)
        return found[0] if found else None


class SqlAdminDelegations(_Reader, AdminDelegationDirectory):
    def active_until(self, shop_id: ShopId, now: datetime) -> datetime | None:
        c = t.admin_access_grant.c
        statement = sa.select(sa.func.max(c.expires_at).label("until")).where(
            c.shop_id == shop_id.value, c.revoked_at.is_(None), c.expires_at > to_db(now)
        )
        rows = self._rows(statement)
        until = rows[0]["until"] if rows else None
        return None if until is None else from_db(until)
