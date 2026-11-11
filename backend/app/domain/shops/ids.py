"""Identifiants typés du socle des boutiques (UUIDv7, specs D5)."""

from app.domain.shared.ids import EntityId


class MerchantAccountId(EntityId):
    """Compte commerçant (client de la plateforme, plusieurs boutiques possibles)."""

    __slots__ = ()


class LocationId(EntityId):
    """Lieu de stock : boutique ou entrepôt."""

    __slots__ = ()


class ShopSettingsId(EntityId):
    """Réglages d'une boutique (un seul jeu par boutique)."""

    __slots__ = ()


class PaymentModeId(EntityId):
    __slots__ = ()


class ExpenseCategoryId(EntityId):
    __slots__ = ()


class MembershipId(EntityId):
    """Rattachement d'un utilisateur à une boutique."""

    __slots__ = ()


class AdminGrantId(EntityId):
    """Délégation d'accès accordée à l'administrateur plateforme (`ADMIN_ACCESS_GRANT`)."""

    __slots__ = ()
