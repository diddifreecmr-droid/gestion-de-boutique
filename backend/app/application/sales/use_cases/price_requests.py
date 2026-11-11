"""UC-VEN-03 — Demandes de prix sous le minimum : demander, décider, lister, lire (T16b).

- `RequestPriceApproval` (`PRICE_REQUEST_CREATE`, vendeur) : article actif dont le minimum est
  actif (réglage H9), prix demandé **strictement** sous ce minimum (sinon 400 : rien à
  demander), lieu = lieu de vente habituel du vendeur (Q-36). Alerte « Demande de prix » aux
  propriétaires (`sales/alerts.py`). Idempotent par `request_id` client (201 puis 200).
- `DecidePriceRequest` (`PRICE_REQUEST_DECIDE`, propriétaire) : accepter / refuser une demande
  **en attente** ; décidée ou expirée → `INVALID_STATE_TRANSITION`. L'alerte est résolue.
- `ListPriceRequests` (`PRICE_REQUEST_READ`) : vendeur → les siennes (portée OWN dans la
  requête), propriétaire → celles **en attente** (statut effectif). `GetPriceRequest` : une
  demande (celle d'un autre vendeur → 404).

Le statut présenté est toujours le statut **effectif** à l'horloge (`status_at`).
"""

from dataclasses import dataclass

from app.application.catalog.ports import ArticleRepository
from app.application.ports.clock import Clock
from app.application.ports.repository import not_found
from app.application.ports.uow import UnitOfWorkFactory
from app.application.sales.resolver import sale_location
from app.application.sales.return_ports import PriceRequestRepository
from app.application.security.access import OwnScope
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop, performer_of, require_version
from app.application.shops.ports import ShopSettingsRepository
from app.domain.catalog.ids import ArticleId
from app.domain.catalog.prices import PriceKind
from app.domain.sales.ids import PriceRequestId
from app.domain.sales.lines import SaleMode
from app.domain.sales.price_request import PriceRequest, PriceRequestStatus
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.money import Money


@dataclass(frozen=True, slots=True)
class PriceRequestView:
    request: PriceRequest
    status: PriceRequestStatus
    """Statut effectif à l'horloge (une demande échue est « Expirée »)."""


@dataclass(frozen=True, slots=True, kw_only=True)
class PriceRequestCommand:
    article_id: ArticleId
    requested_price: int
    sale_mode: SaleMode | None = None
    """« À la pièce » : minimum de la pièce ; sinon minimum de l'unité de vente."""
    request_id: PriceRequestId | None = None


class _PriceRequests:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock

    def _view(self, request: PriceRequest) -> PriceRequestView:
        return PriceRequestView(request, request.status_at(self._clock.now()))


class RequestPriceApproval(_PriceRequests):
    def execute(self, actor: Actor, command: PriceRequestCommand) -> tuple[PriceRequestView, bool]:
        self._policy.require(actor, Permission.PRICE_REQUEST_CREATE)
        now = self._clock.now()
        with self._uow_factory(actor_shop(actor)) as uow:
            requests = PriceRequestRepository.within(uow)
            if command.request_id is not None:
                existing = requests.find(command.request_id)
                if existing is not None:
                    if existing.seller_id != actor.user_id:
                        raise not_found(command.request_id)
                    return self._view(existing), False
            article = ArticleRepository.within(uow).get(command.article_id)
            if not article.is_active:
                msg = "Article archivé : il ne se vend plus"
                raise ValidationFailed(msg, details={"field": "article_id"})
            enabled = ShopSettingsRepository.within(uow).current().values.min_price_enabled
            kind = (
                PriceKind.MINIMUM_PIECE
                if command.sale_mode is SaleMode.PIECE
                else (PriceKind.MINIMUM)
            )
            minimum = article.prices.active_minimum(kind, min_price_enabled=enabled)
            if minimum is None:
                msg = "Aucun prix minimum actif pour cet article : aucune demande nécessaire"
                raise ValidationFailed(msg, details={"field": "article_id"})
            request = PriceRequest.ask(
                uow.shop_id,
                article=(article.id, article.display_name),
                location_id=sale_location(uow, actor, None),
                requested_price=Money.entry(command.requested_price, "requested_price"),
                min_price=minimum,
                performer=performer_of(actor),
                now=now,
                request_id=command.request_id,
            )
            requests.add(request)
            uow.commit()
        return self._view(request), True


class DecidePriceRequest(_PriceRequests):
    def execute(
        self,
        actor: Actor,
        request_id: PriceRequestId,
        *,
        accept: bool,
        version: int | None = None,
    ) -> PriceRequestView:
        self._policy.require(actor, Permission.PRICE_REQUEST_DECIDE)
        with self._uow_factory(actor_shop(actor)) as uow:
            requests = PriceRequestRepository.within(uow)
            request = requests.get(request_id)
            if version is not None:
                require_version(request.version, version)
            request.decide(accept=accept, performer=performer_of(actor), now=self._clock.now())
            requests.update(request)
            uow.commit()
        return self._view(request)


class ListPriceRequests(_PriceRequests):
    def execute(self, actor: Actor) -> list[PriceRequestView]:
        scope = self._policy.scope_filter(actor, Permission.PRICE_REQUEST_READ)
        with self._uow_factory(actor_shop(actor)) as uow:
            requests = PriceRequestRepository.within(uow)
            if isinstance(scope, OwnScope):
                return [self._view(r) for r in requests.for_seller(scope.user_id)]
            views = [self._view(r) for r in requests.pending()]
        return [view for view in views if view.status is PriceRequestStatus.PENDING]


class GetPriceRequest(_PriceRequests):
    def execute(self, actor: Actor, request_id: PriceRequestId) -> PriceRequestView:
        scope = self._policy.scope_filter(actor, Permission.PRICE_REQUEST_READ)
        with self._uow_factory(actor_shop(actor)) as uow:
            request = PriceRequestRepository.within(uow).get(request_id)
        if isinstance(scope, OwnScope) and request.seller_id != scope.user_id:
            raise not_found(request_id)
        return self._view(request)
