"""Dépôts SQL du socle (2/2) : modes de paiement, catégories, rattachements, délégations."""

from datetime import datetime
from typing import Any

import sqlalchemy as sa

from app.application.shops.ports import (
    AdminGrantRepository,
    ExpenseCategoryRepository,
    MembershipRepository,
    PaymentModeRepository,
)
from app.domain.shared.ids import ShopId, UserId
from app.domain.shared.roles import Role
from app.domain.shops.admin_grant import AdminAccessGrant
from app.domain.shops.expense_category import ExpenseCategory
from app.domain.shops.ids import (
    AdminGrantId,
    ExpenseCategoryId,
    LocationId,
    MembershipId,
    PaymentModeId,
)
from app.domain.shops.membership import Membership
from app.domain.shops.payment_mode import PaymentMode, PaymentModeDetails
from app.infrastructure.persistence.sqlalchemy import tables_shops as t
from app.infrastructure.persistence.sqlalchemy.columns import from_db, from_db_optional, to_db
from app.infrastructure.persistence.sqlalchemy.shops import (
    SqlListing,
    SqlLocationRepository,
    SqlShopRepository,
    SqlShopSettingsRepository,
)


class SqlPaymentModeRepository(SqlListing[PaymentModeId, PaymentMode], PaymentModeRepository):
    table = t.payment_mode

    def _to_columns(self, aggregate: PaymentMode) -> dict[str, Any]:
        details = aggregate.details
        return {
            "name": details.name,
            "name_key": aggregate.name_key,
            "reference_required": details.reference_required,
            "active": details.active,
            "display_order": details.display_order,
        }

    def _from_row(self, row: sa.RowMapping) -> PaymentMode:
        details = PaymentModeDetails(
            name=row["name"],
            reference_required=bool(row["reference_required"]),
            active=bool(row["active"]),
            display_order=int(row["display_order"]),
        )
        return PaymentMode(
            id=PaymentModeId(row["id"]),
            shop_id=ShopId(row["shop_id"]),
            details=details,
            version=int(row["version"]),
        )

    def list_all(self) -> list[PaymentMode]:
        c = self.table.c
        return self._select_all(c.display_order, c.name_key, c.id)


class SqlExpenseCategoryRepository(
    SqlListing[ExpenseCategoryId, ExpenseCategory], ExpenseCategoryRepository
):
    table = t.expense_category

    def _to_columns(self, aggregate: ExpenseCategory) -> dict[str, Any]:
        return {
            "name": aggregate.name,
            "name_key": aggregate.name_key,
            "is_base": aggregate.is_base,
            "active": aggregate.active,
            "display_order": aggregate.display_order,
            "requires_description": aggregate.requires_description,
        }

    def _from_row(self, row: sa.RowMapping) -> ExpenseCategory:
        return ExpenseCategory(
            id=ExpenseCategoryId(row["id"]),
            shop_id=ShopId(row["shop_id"]),
            name=row["name"],
            is_base=bool(row["is_base"]),
            active=bool(row["active"]),
            display_order=int(row["display_order"]),
            requires_description=bool(row["requires_description"]),
            version=int(row["version"]),
        )

    def list_all(self) -> list[ExpenseCategory]:
        c = self.table.c
        return self._select_all(c.display_order, c.name_key, c.id)


def membership_from_row(row: sa.RowMapping) -> Membership:
    location = row["default_location_id"]
    return Membership(
        id=MembershipId(row["id"]),
        shop_id=ShopId(row["shop_id"]),
        user_id=UserId(row["user_id"]),
        role=Role(row["role"]),
        default_location_id=None if location is None else LocationId(location),
        active=bool(row["active"]),
        version=int(row["version"]),
    )


class SqlMembershipRepository(SqlListing[MembershipId, Membership], MembershipRepository):
    table = t.membership

    def _to_columns(self, aggregate: Membership) -> dict[str, Any]:
        location = aggregate.default_location_id
        return {
            "user_id": aggregate.user_id.value,
            "role": aggregate.role.value,
            "default_location_id": None if location is None else location.value,
            "active": aggregate.active,
        }

    def _from_row(self, row: sa.RowMapping) -> Membership:
        return membership_from_row(row)

    def find_by_user(self, user_id: UserId) -> Membership | None:
        c = self.table.c
        found = self._select_all(c.id, where=c.user_id == user_id.value)
        return found[0] if found else None

    def list_all(self) -> list[Membership]:
        return self._select_all(self.table.c.id)


class SqlAdminGrantRepository(SqlListing[AdminGrantId, AdminAccessGrant], AdminGrantRepository):
    table = t.admin_access_grant

    def _to_columns(self, aggregate: AdminAccessGrant) -> dict[str, Any]:
        revoked_by = aggregate.revoked_by
        return {
            "granted_by": aggregate.granted_by.value,
            "granted_at": to_db(aggregate.granted_at),
            "expires_at": to_db(aggregate.expires_at),
            "revoked_at": None if aggregate.revoked_at is None else to_db(aggregate.revoked_at),
            "revoked_by": None if revoked_by is None else revoked_by.value,
        }

    def _from_row(self, row: sa.RowMapping) -> AdminAccessGrant:
        revoked_by = row["revoked_by"]
        return AdminAccessGrant(
            id=AdminGrantId(row["id"]),
            shop_id=ShopId(row["shop_id"]),
            granted_by=UserId(row["granted_by"]),
            granted_at=from_db(row["granted_at"]),
            expires_at=from_db(row["expires_at"]),
            revoked_at=from_db_optional(row["revoked_at"]),
            revoked_by=None if revoked_by is None else UserId(revoked_by),
            version=int(row["version"]),
        )

    def active(self, now: datetime) -> AdminAccessGrant | None:
        c = self.table.c
        running = self._select_all(
            c.granted_at,
            c.id,
            where=sa.and_(c.revoked_at.is_(None), c.expires_at > to_db(now)),
        )
        return running[-1] if running else None


SQL_SHOP_REPOSITORIES = (
    SqlShopRepository,
    SqlShopSettingsRepository,
    SqlLocationRepository,
    SqlPaymentModeRepository,
    SqlExpenseCategoryRepository,
    SqlMembershipRepository,
    SqlAdminGrantRepository,
)
