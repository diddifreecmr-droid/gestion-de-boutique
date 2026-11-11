"""Agrégat `PriceRequest` : demande d'accord pour un prix sous le minimum (UC-VEN-03, H9).

- Le vendeur demande un prix (`requested_price`) **strictement** sous le minimum actif de
  l'article (`min_price`, copié au moment de la demande) ; le propriétaire reçoit l'alerte
  « Demande de prix » (article, prix demandé, minimum, vendeur) et répond Accepter / Refuser.
- Statuts : En attente → Acceptée | Refusée | Expirée ; Acceptée → Expirée si elle n'a pas
  servi à temps. Une demande décidée ou expirée ne se décide plus (`INVALID_STATE_TRANSITION`).
- **Q-44 tranchée** :
  - expiration **30 minutes** après la demande, frontière incluse (à 30:00 pile : expirée) ;
  - une demande **acceptée** vaut 30 minutes à compter de l'accord (le vendeur a le temps de
    valider) ; passé ce délai, elle est « Expirée » ;
  - **usage unique** : liée à la vente qui l'exploite (`sale_id`), elle ne sert plus ;
  - le prix vendu doit être **au moins** le prix accordé (vendre plus cher reste permis).
- Le statut tenu en base peut retarder sur l'horloge (le worker `ExpirePriceRequests`, TR-19,
  le rattrape) : `status_at(now)` donne le statut **effectif**, seul lu par les règles.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum

from app.domain.audit.events import NotAudited
from app.domain.audit.values import EntityRef, Performer
from app.domain.catalog.ids import ArticleId
from app.domain.sales import events as ev
from app.domain.sales.ids import PriceRequestId, SaleId
from app.domain.shared.business_day import require_aware
from app.domain.shared.errors import InvalidStateTransition, ValidationFailed
from app.domain.shared.events import DomainEvent, EventCollector
from app.domain.shared.ids import ShopId, UserId
from app.domain.shared.money import Money
from app.domain.shops.ids import LocationId

PRICE_REQUEST_TTL = timedelta(minutes=30)


class PriceRequestStatus(StrEnum):
    PENDING = "pending"  # En attente
    ACCEPTED = "accepted"  # Acceptée
    REFUSED = "refused"  # Refusée
    EXPIRED = "expired"  # Expirée


@dataclass(frozen=True, kw_only=True)
class PriceRequestExpired(DomainEvent, NotAudited):
    """Expiration constatée par le worker : l'alerte du propriétaire est résolue (ERR-PRM-09)."""

    request_key: str


def request_key(request_id: PriceRequestId) -> str:
    """Clé de déduplication de l'alerte « Demande de prix »."""
    return f"price_request:{request_id}"


@dataclass(eq=False, kw_only=True)
class PriceRequest:
    id: PriceRequestId
    shop_id: ShopId
    seller_id: UserId
    article_id: ArticleId
    article_name: str
    location_id: LocationId
    requested_price: Money
    min_price: Money
    requested_at: datetime
    expires_at: datetime
    status: PriceRequestStatus = PriceRequestStatus.PENDING
    decided_by: UserId | None = None
    decided_at: datetime | None = None
    sale_id: SaleId | None = None
    version: int = 0
    events: EventCollector = field(default_factory=EventCollector, repr=False)

    def __post_init__(self) -> None:
        self.status = PriceRequestStatus(self.status)
        self.requested_at = require_aware(self.requested_at)
        self.expires_at = require_aware(self.expires_at)
        if self.decided_at is not None:
            self.decided_at = require_aware(self.decided_at)

    @property
    def entity(self) -> EntityRef:
        return EntityRef("price_request", self.id.value, self.article_name[:500])

    @property
    def key(self) -> str:
        return request_key(self.id)

    @classmethod
    def ask(
        cls,
        shop_id: ShopId,
        *,
        article: tuple[ArticleId, str],
        location_id: LocationId,
        requested_price: Money,
        min_price: Money,
        performer: Performer,
        now: datetime,
        request_id: PriceRequestId | None = None,
    ) -> "PriceRequest":
        requested_price.require_non_negative("requested_price")
        if requested_price >= min_price:
            msg = "Prix au moins égal au minimum : aucune demande nécessaire"
            raise ValidationFailed(msg, details={"field": "requested_price"})
        request = cls(
            id=request_id or PriceRequestId.new(),
            shop_id=shop_id,
            seller_id=performer.user_id,
            article_id=article[0],
            article_name=article[1],
            location_id=location_id,
            requested_price=requested_price,
            min_price=min_price,
            requested_at=now,
            expires_at=now + PRICE_REQUEST_TTL,
        )
        summary = f"Demande de prix : {article[1]} à {requested_price} (minimum {min_price})"
        request.events.record(
            ev.PriceRequested(
                shop_id=shop_id,
                occurred_at=now,
                performer=performer,
                entity=request.entity,
                summary=summary[:500],
                request_key=request.key,
            )
        )
        return request

    # ------------------------------------------------------------------ lectures
    def status_at(self, now: datetime) -> PriceRequestStatus:
        """Statut effectif : une demande en attente ou acceptée non utilisée expire à l'heure."""
        open_ = self.status is PriceRequestStatus.PENDING or (
            self.status is PriceRequestStatus.ACCEPTED and self.sale_id is None
        )
        if open_ and now >= self.expires_at:
            return PriceRequestStatus.EXPIRED
        return self.status

    def usable_at(self, now: datetime) -> bool:
        return self.status_at(now) is PriceRequestStatus.ACCEPTED and self.sale_id is None

    # ------------------------------------------------------------------ cycle de vie
    def decide(self, *, accept: bool, performer: Performer, now: datetime) -> None:
        current = self.status_at(now)
        if current is not PriceRequestStatus.PENDING:
            msg = "Cette demande de prix n'est plus en attente"
            raise InvalidStateTransition(msg, details={"status": current.value})
        self.status = PriceRequestStatus.ACCEPTED if accept else PriceRequestStatus.REFUSED
        self.decided_by, self.decided_at = performer.user_id, now
        if accept:
            self.expires_at = now + PRICE_REQUEST_TTL
        event = ev.PriceRequestAccepted if accept else ev.PriceRequestRefused
        verdict = "acceptée" if accept else "refusée"
        self.events.record(
            event(
                shop_id=self.shop_id,
                occurred_at=now,
                performer=performer,
                entity=self.entity,
                summary=f"Demande de prix {verdict} : {self.article_name} à {self.requested_price}"[
                    :500
                ],
                request_key=self.key,
            )
        )

    def use(self, sale_id: SaleId, now: datetime) -> None:
        """La vente exploite l'accord : il ne servira plus (usage unique)."""
        if not self.usable_at(now):
            msg = "Demande de prix inutilisable"
            raise InvalidStateTransition(msg, details={"status": self.status_at(now).value})
        self.sale_id = sale_id

    def expire(self, now: datetime) -> bool:
        """Worker (TR-19) : inscrit l'expiration ; `False` si rien à faire (idempotent)."""
        if self.status is PriceRequestStatus.EXPIRED:
            return False
        if self.status_at(now) is not PriceRequestStatus.EXPIRED:
            return False
        self.status = PriceRequestStatus.EXPIRED
        self.events.record(
            PriceRequestExpired(shop_id=self.shop_id, occurred_at=now, request_key=self.key)
        )
        return True
