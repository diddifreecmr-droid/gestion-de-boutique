"""Dépôts mémoire **plateforme** : `User`, `DeviceSession`, `MerchantAccount` (aucun `shop_id`).

Comme les dépôts de boutique, les agrégats sont **copiés** à l'écriture et à la lecture
(`copy.deepcopy`) ; la copie stockée est purgée de ses événements en attente. L'unicité
(téléphone d'un utilisateur, d'un compte) vaut sur toute la plateforme.
"""

import copy
from collections.abc import Hashable
from typing import ClassVar, cast

from app.application.identity.repositories import (
    DeviceSessionRepository,
    MerchantAccountRepository,
    PlatformAggregate,
    PlatformRepository,
    PlatformTracker,
    UserRepository,
)
from app.domain.identity.events import SessionId
from app.domain.identity.phone import PhoneNumber
from app.domain.identity.session import DeviceSession
from app.domain.identity.user import User
from app.domain.shared.ids import DeviceId, EntityId, UserId
from app.domain.shops.account import MerchantAccount
from app.domain.shops.ids import MerchantAccountId
from app.infrastructure.persistence.memory.platform_store import (
    MemoryPlatformTransaction,
    PlatformRow,
)

USER_PHONE = "user_phone"
ACCOUNT_PHONE = "merchant_account_phone"


class MemoryPlatformRepository[IdT: EntityId, AggT: PlatformAggregate](
    PlatformRepository[IdT, AggT]
):
    table: ClassVar[str]

    def __init__(self, tracker: PlatformTracker, transaction: MemoryPlatformTransaction) -> None:
        super().__init__(tracker)
        self._transaction = transaction

    def _unique(self, aggregate: AggT) -> dict[str, Hashable]:
        return {}

    def _all(self) -> list[AggT]:
        # Les lignes de cette table ne sont construites que par `_row` à partir d'un AggT.
        rows = self._transaction.visible(self.table).values()
        return [cast(AggT, copy.deepcopy(row.payload)) for row in rows]

    def _load(self, entity_id: IdT) -> AggT | None:
        row = self._transaction.visible(self.table).get(entity_id)
        return None if row is None else cast(AggT, copy.deepcopy(row.payload))

    def _insert(self, aggregate: AggT) -> None:
        self._transaction.insert(self.table, self._row(aggregate))

    def _save(self, aggregate: AggT, *, expected_version: int) -> None:
        self._transaction.update(self.table, self._row(aggregate), expected_version)

    def _row(self, aggregate: AggT) -> PlatformRow:
        snapshot = copy.deepcopy(aggregate)
        snapshot.events.pull()
        return PlatformRow(aggregate.id, aggregate.version, self._unique(aggregate), snapshot)


class MemoryUserRepository(MemoryPlatformRepository[UserId, User], UserRepository):
    table = "users"

    def _unique(self, aggregate: User) -> dict[str, Hashable]:
        return {USER_PHONE: aggregate.phone.e164}

    def find_by_phone(self, phone: PhoneNumber) -> User | None:
        matches = [user for user in self._all() if user.phone == phone]
        return self._tracked(matches)[0] if matches else None


class MemoryDeviceSessionRepository(
    MemoryPlatformRepository[SessionId, DeviceSession], DeviceSessionRepository
):
    table = "device_sessions"

    def for_user(self, user_id: UserId) -> list[DeviceSession]:
        sessions = [s for s in self._all() if s.user_id == user_id]
        return self._tracked(sorted(sessions, key=lambda s: (s.created_at, s.id)))

    def active_for_device(self, user_id: UserId, device_id: DeviceId) -> DeviceSession | None:
        candidates = [
            s for s in self.for_user(user_id) if s.device_id == device_id and not s.revoked
        ]
        return candidates[-1] if candidates else None


class MemoryMerchantAccountRepository(
    MemoryPlatformRepository[MerchantAccountId, MerchantAccount], MerchantAccountRepository
):
    table = "merchant_accounts"

    def _unique(self, aggregate: MerchantAccount) -> dict[str, Hashable]:
        return {ACCOUNT_PHONE: aggregate.phone.e164}

    def find_by_phone(self, phone: PhoneNumber) -> MerchantAccount | None:
        matches = [account for account in self._all() if account.phone == phone]
        return self._tracked(matches)[0] if matches else None
