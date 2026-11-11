"""Ports de l'identité (T08) : cryptographie, jetons, rattachements, handlers d'événements.

**Portée « plateforme ».** Un utilisateur n'appartient à aucune boutique : son téléphone est
unique sur toute la plateforme (CDC § 20.1) et il peut être rattaché à plusieurs boutiques.
L'`UnitOfWork` de T05 est lié à **une** boutique ; plutôt que d'inventer une pseudo-boutique
« plateforme » (qui affaiblirait l'isolation), l'identité a sa **propre** unité de travail,
`IdentityUnitOfWork` (`uow.py`), et ses propres dépôts sans `shop_id` (`repositories.py`). Ils
ne servent que les agrégats `User` et `DeviceSession` ; aucune donnée de boutique n'y transite.
Les ports existants (`app.application.ports`) ne sont pas modifiés.

**Rattachements.** `MEMBERSHIP` n'existe pas encore (T10) : `MembershipDirectory` est un port
de **lecture** minimal (boutiques et rôles d'un utilisateur), relu à chaque requête pour
construire l'`Actor` (specs § 8.1). T10 l'implémentera sur le vrai agrégat.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from app.application.security.actor import require_utc
from app.application.security.roles import Role
from app.domain.identity.events import IdentityEvent, SessionId
from app.domain.shared.ids import ShopId, UserId

if TYPE_CHECKING:
    from app.application.identity.uow import IdentityUnitOfWork


class PasswordHasher(ABC):
    """Hachage lent et salé des secrets (codes et mots de passe)."""

    @abstractmethod
    def hash(self, secret: str) -> str:
        """Empreinte autoportante (algorithme, paramètres, sel compris)."""

    @abstractmethod
    def verify(self, secret_hash: str, secret: str) -> bool:
        """Vrai si `secret` correspond ; faux s'il diffère ; lève si l'empreinte est illisible."""

    @abstractmethod
    def needs_rehash(self, secret_hash: str) -> bool:
        """Vrai si l'empreinte a été produite avec des paramètres plus faibles qu'aujourd'hui."""


@dataclass(frozen=True, slots=True, kw_only=True)
class AccessClaims:
    """Contenu du jeton d'accès. Le rôle n'y figure **pas** (relu par boutique, § 8.1)."""

    user_id: UserId
    session_id: SessionId
    is_platform_admin: bool
    issued_at: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        require_utc(self.issued_at, "AccessClaims.issued_at")
        require_utc(self.expires_at, "AccessClaims.expires_at")
        if self.expires_at <= self.issued_at:
            msg = "Un jeton d'accès expire après son émission"
            raise ValueError(msg)


class TokenService(ABC):
    """Jetons d'accès signés, courts (15 min)."""

    @abstractmethod
    def issue(self, claims: AccessClaims) -> str: ...

    @abstractmethod
    def verify(self, token: str) -> AccessClaims:
        """Claims d'un jeton valide ; `Unauthenticated` s'il est illisible, falsifié ou expiré."""


class RefreshSecrets(ABC):
    """Secrets opaques des jetons de rafraîchissement : seule leur empreinte est stockée."""

    @abstractmethod
    def generate(self) -> str:
        """Secret aléatoire neuf (≥ 256 bits d'entropie), sûr dans un cookie."""

    @abstractmethod
    def digest(self, secret: str) -> str:
        """Empreinte déterministe, comparable à celle stockée dans la session."""


class TemporaryPinGenerator(ABC):
    """Codes provisoires remis par le propriétaire (UC-SOC-04, `ResetPin`)."""

    @abstractmethod
    def generate(self) -> str:
        """Code de 6 chiffres tiré au hasard (cryptographiquement sûr)."""


@dataclass(frozen=True, slots=True, kw_only=True)
class MembershipView:
    """Rattachement lu : rôle de l'utilisateur dans une boutique (un seul par boutique)."""

    shop_id: ShopId
    shop_name: str
    role: Role
    active: bool


class MembershipDirectory(ABC):
    """Lecture des rattachements (T10 fournira l'adaptateur sur l'agrégat `MEMBERSHIP`)."""

    @abstractmethod
    def for_user(self, user_id: UserId) -> Sequence[MembershipView]:
        """Tous les rattachements de l'utilisateur, actifs ou non, triés par nom de boutique."""

    @abstractmethod
    def find(self, user_id: UserId, shop_id: ShopId) -> MembershipView | None:
        """Rattachement de l'utilisateur à cette boutique (actif ou non), ou `None`."""


class IdentityEventHandler(ABC):
    """Reçoit les événements de l'identité dans la transaction (journal T09)."""

    @abstractmethod
    def handle(self, event: IdentityEvent, uow: "IdentityUnitOfWork") -> None:
        """Toute exception annule la transaction entière."""
