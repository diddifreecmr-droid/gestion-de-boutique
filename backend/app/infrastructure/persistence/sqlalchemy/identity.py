"""Dépôts SQL plateforme : `User` (`app_user`), `DeviceSession`, `MerchantAccount` (T10).

Correspondance agrégat ↔ colonnes : les deux compteurs d'essais (`LockoutCounter`) sont
aplatis en `failed_attempts`/`locked_until` et `pin_change_failures`/`pin_change_locked_until`.
"""

from collections.abc import Mapping
from typing import Any, ClassVar

import sqlalchemy as sa

from app.application.identity.repositories import (
    DeviceSessionRepository,
    MerchantAccountRepository,
    UserRepository,
)
from app.domain.identity.events import SessionId
from app.domain.identity.lockout import LockoutCounter
from app.domain.identity.phone import PhoneNumber
from app.domain.identity.session import DeviceSession
from app.domain.identity.status import UserStatus
from app.domain.identity.user import User
from app.domain.plans.entitlements import PlanCode
from app.domain.shared.ids import DeviceId, ShopId, UserId
from app.domain.shops.account import MerchantAccount
from app.domain.shops.ids import MerchantAccountId
from app.domain.shops.values import AccountStatus
from app.infrastructure.persistence.sqlalchemy.columns import from_db, from_db_optional, to_db
from app.infrastructure.persistence.sqlalchemy.platform_repositories import SqlPlatformRepository
from app.infrastructure.persistence.sqlalchemy.tables_identity import (
    app_user,
    device_session,
    merchant_account,
)


def _optional(instant: Any) -> Any:
    return None if instant is None else to_db(instant)


class SqlUserRepository(SqlPlatformRepository[UserId, User], UserRepository):
    table = app_user
    unique: ClassVar[Mapping[str, str]] = {"user_phone": "phone"}

    def _to_columns(self, aggregate: User) -> dict[str, Any]:
        login, pin = aggregate.login_lockout, aggregate.pin_change_lockout
        return {
            "phone": aggregate.phone.e164,
            "name": aggregate.name,
            "secret_hash": aggregate.secret_hash,
            "is_platform_admin": aggregate.is_platform_admin,
            "must_change_pin": aggregate.must_change_pin,
            "status": aggregate.status.value,
            "failed_attempts": login.failures,
            "locked_until": _optional(login.locked_until),
            "pin_change_failures": pin.failures,
            "pin_change_locked_until": _optional(pin.locked_until),
            "last_login_at": _optional(aggregate.last_login_at),
        }

    def _from_row(self, row: sa.RowMapping) -> User:
        return User(
            UserId(row["id"]),
            PhoneNumber(row["phone"]),
            row["name"],
            row["secret_hash"],
            is_platform_admin=bool(row["is_platform_admin"]),
            must_change_pin=bool(row["must_change_pin"]),
            status=UserStatus(row["status"]),
            login_lockout=LockoutCounter(
                int(row["failed_attempts"]), from_db_optional(row["locked_until"])
            ),
            pin_change_lockout=LockoutCounter(
                int(row["pin_change_failures"]), from_db_optional(row["pin_change_locked_until"])
            ),
            last_login_at=from_db_optional(row["last_login_at"]),
            version=int(row["version"]),
        )

    def find_by_phone(self, phone: PhoneNumber) -> User | None:
        found = self._select(self.table.c.phone == phone.e164)
        return found[0] if found else None


class SqlDeviceSessionRepository(
    SqlPlatformRepository[SessionId, DeviceSession], DeviceSessionRepository
):
    table = device_session

    def _to_columns(self, aggregate: DeviceSession) -> dict[str, Any]:
        return {
            "user_id": aggregate.user_id.value,
            "device_id": aggregate.device_id.value,
            "device_label": aggregate.device_label,
            "refresh_hash": aggregate.refresh_hash,
            "created_at": to_db(aggregate.created_at),
            "last_seen": to_db(aggregate.last_seen),
            "expires_at": to_db(aggregate.expires_at),
            "sliding": aggregate.sliding,
            "revoked": aggregate.revoked,
            "revoked_at": _optional(aggregate.revoked_at),
        }

    def _from_row(self, row: sa.RowMapping) -> DeviceSession:
        return DeviceSession(
            id=SessionId(row["id"]),
            user_id=UserId(row["user_id"]),
            device_id=DeviceId(row["device_id"]),
            device_label=row["device_label"],
            refresh_hash=row["refresh_hash"],
            created_at=from_db(row["created_at"]),
            last_seen=from_db(row["last_seen"]),
            expires_at=from_db(row["expires_at"]),
            sliding=bool(row["sliding"]),
            revoked=bool(row["revoked"]),
            revoked_at=from_db_optional(row["revoked_at"]),
            version=int(row["version"]),
        )

    def for_user(self, user_id: UserId) -> list[DeviceSession]:
        c = self.table.c
        return self._select(c.user_id == user_id.value, order_by=(c.created_at, c.id))

    def active_for_device(self, user_id: UserId, device_id: DeviceId) -> DeviceSession | None:
        c = self.table.c
        found = self._select(
            c.user_id == user_id.value,
            c.device_id == device_id.value,
            c.revoked.is_(False),
            order_by=(c.created_at, c.id),
        )
        return found[-1] if found else None


class SqlMerchantAccountRepository(
    SqlPlatformRepository[MerchantAccountId, MerchantAccount], MerchantAccountRepository
):
    table = merchant_account
    unique: ClassVar[Mapping[str, str]] = {"merchant_account_phone": "phone"}

    def _to_columns(self, aggregate: MerchantAccount) -> dict[str, Any]:
        shops = sorted(aggregate.shop_names.items(), key=lambda item: item[0])
        return {
            "name": aggregate.name,
            "phone": aggregate.phone.e164,
            "plan": aggregate.plan.value,
            "status": aggregate.status.value,
            "shop_names": [{"shop_id": str(shop), "name": name} for shop, name in shops],
        }

    def _from_row(self, row: sa.RowMapping) -> MerchantAccount:
        return MerchantAccount(
            id=MerchantAccountId(row["id"]),
            name=row["name"],
            phone=PhoneNumber(row["phone"]),
            plan=PlanCode(row["plan"]),
            status=AccountStatus(row["status"]),
            shop_names={ShopId.parse(item["shop_id"]): item["name"] for item in row["shop_names"]},
            version=int(row["version"]),
        )

    def find_by_phone(self, phone: PhoneNumber) -> MerchantAccount | None:
        found = self._select(self.table.c.phone == phone.e164)
        return found[0] if found else None
