"""Dépôts **plateforme** : `User`, `DeviceSession` et `MerchantAccount` (aucun `shop_id`).

Même sémantique que le gabarit `Repository` de T05, sans la boutique :

- `get(id)` lève `NotFound` si absent ; `add` exige la version 0 et la passe à 1 ;
  `update` applique le verrou optimiste (`VersionConflict`) ;
- unicité **sur toute la plateforme** (téléphone d'un utilisateur, d'un compte commerçant)
  → `Duplicate`.

Un adaptateur fournit `_load`, `_insert`, `_save` et les requêtes propres à chaque port.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Protocol

from app.application.ports.repository import not_found
from app.domain.identity.events import IdentityEvents, SessionId
from app.domain.identity.phone import PhoneNumber
from app.domain.identity.session import DeviceSession
from app.domain.identity.user import User
from app.domain.shared.ids import DeviceId, EntityId, UserId
from app.domain.shops.account import MerchantAccount
from app.domain.shops.ids import MerchantAccountId


class PlatformAggregate(Protocol):
    version: int

    @property
    def id(self) -> EntityId: ...

    @property
    def events(self) -> IdentityEvents: ...


class PlatformTracker(Protocol):
    def track(self, aggregate: PlatformAggregate, *, saved: bool) -> None: ...


class PlatformRepository[IdT: EntityId, AggT: PlatformAggregate](ABC):
    """Gabarit des dépôts plateforme, lié à une transaction de l'`IdentityUnitOfWork`."""

    def __init__(self, tracker: PlatformTracker) -> None:
        self._tracker = tracker

    def get(self, entity_id: IdT) -> AggT:
        aggregate = self.find(entity_id)
        if aggregate is None:
            raise not_found(entity_id)
        return aggregate

    def find(self, entity_id: IdT) -> AggT | None:
        aggregate = self._load(entity_id)
        if aggregate is not None:
            self._tracker.track(aggregate, saved=False)
        return aggregate

    def add(self, aggregate: AggT) -> None:
        if aggregate.version != 0:
            msg = f"add attend un agrégat neuf (version 0), reçu la version {aggregate.version}"
            raise ValueError(msg)
        aggregate.version = 1
        try:
            self._insert(aggregate)
        except BaseException:
            aggregate.version = 0
            raise
        self._tracker.track(aggregate, saved=True)

    def update(self, aggregate: AggT) -> None:
        expected = aggregate.version
        if expected < 1:
            msg = "update attend un agrégat déjà enregistré (version ≥ 1) : utiliser add"
            raise ValueError(msg)
        aggregate.version = expected + 1
        try:
            self._save(aggregate, expected_version=expected)
        except BaseException:
            aggregate.version = expected
            raise
        self._tracker.track(aggregate, saved=True)

    def _tracked(self, aggregates: Sequence[AggT]) -> list[AggT]:
        """À appeler par les requêtes des adaptateurs sur chaque agrégat renvoyé."""
        for aggregate in aggregates:
            self._tracker.track(aggregate, saved=False)
        return list(aggregates)

    @abstractmethod
    def _load(self, entity_id: IdT) -> AggT | None: ...

    @abstractmethod
    def _insert(self, aggregate: AggT) -> None:
        """Agrégat déjà en version 1 ; `Duplicate` si l'id ou une clé unique est pris."""

    @abstractmethod
    def _save(self, aggregate: AggT, *, expected_version: int) -> None:
        """`NotFound` si absent, `VersionConflict` si la version stockée diffère."""


class UserRepository(PlatformRepository[UserId, User]):
    """Comptes ; le téléphone (E.164) est unique sur toute la plateforme."""

    @abstractmethod
    def find_by_phone(self, phone: PhoneNumber) -> User | None: ...


class DeviceSessionRepository(PlatformRepository[SessionId, DeviceSession]):
    """Sessions d'appareil."""

    @abstractmethod
    def for_user(self, user_id: UserId) -> list[DeviceSession]:
        """Toutes les sessions de l'utilisateur (révoquées comprises), plus anciennes d'abord."""

    @abstractmethod
    def active_for_device(self, user_id: UserId, device_id: DeviceId) -> DeviceSession | None:
        """Session non révoquée de cet utilisateur sur cet appareil, s'il y en a une."""


class MerchantAccountRepository(PlatformRepository[MerchantAccountId, MerchantAccount]):
    """Comptes commerçants (T10) ; le téléphone principal est unique sur la plateforme."""

    @abstractmethod
    def find_by_phone(self, phone: PhoneNumber) -> MerchantAccount | None: ...
