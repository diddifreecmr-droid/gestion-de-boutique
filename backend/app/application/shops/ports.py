"""Ports du socle des boutiques (T10) : dépôts liés à la boutique et lectures plateforme.

Dépôts (gabarit `Repository` de T05, `Port.within(uow)`) : boutique, réglages, lieux, modes de
paiement, catégories de dépense, rattachements, délégations. Les contraintes `UniqueKey`
portent le nom de la contrainte SQL (`tables_shops.py`).

`ShopCatalog` : lecture **plateforme** des boutiques (console de l'administrateur, offre d'une
boutique), sur l'état validé — elle traverse les boutiques et ne sert qu'à l'administrateur.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from app.application.ports.aggregate import Aggregate, UniqueKey
from app.application.ports.errors import IsolationViolation
from app.application.ports.repository import Repository
from app.domain.plans.entitlements import PlanCode
from app.domain.profiles.modules import Module
from app.domain.profiles.profile import ProfileCode
from app.domain.shared.ids import EntityId, ShopId, UserId
from app.domain.shops.admin_grant import AdminAccessGrant
from app.domain.shops.expense_category import ExpenseCategory
from app.domain.shops.ids import (
    AdminGrantId,
    ExpenseCategoryId,
    LocationId,
    MembershipId,
    MerchantAccountId,
    PaymentModeId,
    ShopSettingsId,
)
from app.domain.shops.location import Location
from app.domain.shops.membership import Membership
from app.domain.shops.payment_mode import PaymentMode
from app.domain.shops.settings import ShopSettings
from app.domain.shops.shop import Shop
from app.domain.shops.values import ShopStatus

SETTINGS_SINGLETON = "shop_settings_shop"
LOCATION_NAME = "location_name"
PAYMENT_MODE_NAME = "payment_mode_name"
EXPENSE_CATEGORY_NAME = "expense_category_name"
MEMBERSHIP_USER = "membership_user"


class ShopRecordRepository[IdT: EntityId, AggT: Aggregate](Repository[IdT, AggT]):
    """`Repository` + `find` (sans exception) et suivi des listes renvoyées."""

    def find(self, entity_id: IdT) -> AggT | None:
        aggregate = self._load(entity_id)
        if aggregate is None:
            return None
        if aggregate.shop_id != self.shop_id:
            msg = f"{type(self).__name__}._load a renvoyé un agrégat d'une autre boutique"
            raise IsolationViolation(msg)
        self._tracker.track(aggregate, saved=False)
        return aggregate

    def _tracked(self, aggregates: Sequence[AggT]) -> list[AggT]:
        for aggregate in aggregates:
            self._tracker.track(aggregate, saved=False)
        return list(aggregates)


class ShopRepository(ShopRecordRepository[ShopId, Shop]):
    def current(self) -> Shop:
        """La boutique de l'unité de travail (`NotFound` si elle n'existe pas)."""
        return self.get(self.shop_id)


class ShopSettingsRepository(ShopRecordRepository[ShopSettingsId, ShopSettings]):
    def unique_keys(self) -> Sequence[UniqueKey[ShopSettings]]:
        return (UniqueKey(SETTINGS_SINGLETON, lambda settings: "shop"),)

    @abstractmethod
    def current(self) -> ShopSettings:
        """Les réglages de la boutique ; `NotFound` s'ils n'existent pas (boutique inconnue)."""


class LocationRepository(ShopRecordRepository[LocationId, Location]):
    def unique_keys(self) -> Sequence[UniqueKey[Location]]:
        return (UniqueKey(LOCATION_NAME, lambda location: location.name_key),)

    @abstractmethod
    def list_all(self) -> list[Location]:
        """Tous les lieux (inactifs compris), par ordre d'affichage puis par nom."""


class PaymentModeRepository(ShopRecordRepository[PaymentModeId, PaymentMode]):
    def unique_keys(self) -> Sequence[UniqueKey[PaymentMode]]:
        return (UniqueKey(PAYMENT_MODE_NAME, lambda mode: mode.name_key),)

    @abstractmethod
    def list_all(self) -> list[PaymentMode]:
        """Tous les modes (inactifs compris), par ordre d'affichage puis par nom."""


class ExpenseCategoryRepository(ShopRecordRepository[ExpenseCategoryId, ExpenseCategory]):
    def unique_keys(self) -> Sequence[UniqueKey[ExpenseCategory]]:
        return (UniqueKey(EXPENSE_CATEGORY_NAME, lambda category: category.name_key),)

    @abstractmethod
    def list_all(self) -> list[ExpenseCategory]:
        """Toutes les catégories, par ordre d'affichage puis par nom."""


class MembershipRepository(ShopRecordRepository[MembershipId, Membership]):
    def unique_keys(self) -> Sequence[UniqueKey[Membership]]:
        return (UniqueKey(MEMBERSHIP_USER, lambda membership: membership.user_id),)

    @abstractmethod
    def find_by_user(self, user_id: UserId) -> Membership | None: ...

    @abstractmethod
    def list_all(self) -> list[Membership]:
        """Tous les rattachements (inactifs compris), du plus ancien au plus récent."""


class AdminGrantRepository(ShopRecordRepository[AdminGrantId, AdminAccessGrant]):
    @abstractmethod
    def active(self, now: datetime) -> AdminAccessGrant | None:
        """Délégation non retirée et non expirée à `now` (la plus récente), ou `None`."""


@dataclass(frozen=True, slots=True, kw_only=True)
class ShopSummary:
    """Ligne de la console plateforme (TR-23) : boutique, type, statut, modules, compte, offre."""

    shop_id: ShopId
    name: str
    profile_code: ProfileCode
    city: str
    status: ShopStatus
    enabled_modules: frozenset[Module]
    account_id: MerchantAccountId
    account_name: str
    plan: PlanCode
    created_at: datetime


class ShopCatalog(ABC):
    """Boutiques de la plateforme (état validé) ; jamais exposé à un membre de boutique."""

    @abstractmethod
    def list_all(self) -> Sequence[ShopSummary]:
        """Toutes les boutiques, triées par nom puis par identifiant."""

    @abstractmethod
    def find(self, shop_id: ShopId) -> ShopSummary | None: ...
