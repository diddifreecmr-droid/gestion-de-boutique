"""UC-STK-08 — Faire un ajustement ponctuel (comptable, propriétaire ; recette ADJ-01 à ADJ-05).

1. Lieu, article, sens, quantité > 0 dans l'unité de stock (1,5 moto → 400), état, motif de la
   liste du CDC (« Autre » exige une note ; « écart d'inventaire » est réservé aux inventaires),
   photo facultative.
2. Ajustement - supérieur au stock du lieu → `STOCK_INSUFFICIENT` (422, ERR-STK-04).
3. Journal « sensible » ; ajustement fait par le comptable → alerte au propriétaire (ADJ-03).

Idempotent : un `adjustment_id` déjà connu renvoie l'ajustement existant, sans second
mouvement. Rejoué sur conflit de concurrence (`with_stock_retry`).
"""

from dataclasses import dataclass
from decimal import Decimal

from app.application.catalog.ports import ArticleRepository
from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWorkFactory
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop, performer_of
from app.application.stock.adjusting import AdjustmentResult, post_adjustment
from app.application.stock.ledger import StockLedger
from app.application.stock.ports import AdjustmentRepository
from app.application.stock.retry import with_stock_retry
from app.domain.catalog.ids import ArticleId, AttachmentId
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.quantity import Quantity
from app.domain.shops.ids import LocationId
from app.domain.stock.adjustment import (
    MANUAL_REASONS,
    AdjustmentDirection,
    AdjustmentDraft,
    AdjustmentReason,
)
from app.domain.stock.ids import AdjustmentId
from app.domain.stock.values import StockCondition


@dataclass(frozen=True, slots=True, kw_only=True)
class AdjustmentCommand:
    location_id: LocationId
    article_id: ArticleId
    direction: AdjustmentDirection
    quantity: Decimal | str
    condition: StockCondition
    reason: AdjustmentReason
    note: str | None = None
    photo_id: AttachmentId | None = None
    adjustment_id: AdjustmentId | None = None


class RecordAdjustment:
    def __init__(
        self, uow_factory: UnitOfWorkFactory, policy: Policy, ledger: StockLedger, clock: Clock
    ) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._ledger = ledger
        self._clock = clock

    def execute(self, actor: Actor, command: AdjustmentCommand) -> AdjustmentResult:
        self._policy.require(actor, Permission.STOCK_ADJUST)
        if AdjustmentReason(command.reason) not in MANUAL_REASONS:
            msg = "Motif réservé aux écarts d'inventaire"
            raise ValidationFailed(msg, details={"field": "reason"})
        return with_stock_retry(lambda: self._attempt(actor, command))

    def _attempt(self, actor: Actor, command: AdjustmentCommand) -> AdjustmentResult:
        with self._uow_factory(actor_shop(actor)) as uow:
            if command.adjustment_id is not None:
                existing = AdjustmentRepository.within(uow).find(command.adjustment_id)
                if existing is not None:
                    return AdjustmentResult(existing, None)
            article = ArticleRepository.within(uow).get(command.article_id)
            quantity = Quantity.of(command.quantity, article.details.fields.stock_unit)
            draft = AdjustmentDraft(
                location_id=command.location_id,
                article_id=article.id,
                direction=command.direction,
                quantity=quantity,
                condition=command.condition,
                reason=command.reason,
                note=command.note,
                photo_id=command.photo_id,
                adjustment_id=command.adjustment_id,
            )
            result = post_adjustment(
                uow, self._ledger, draft, performer=performer_of(actor), now=self._clock.now()
            )
            uow.commit()
        return result
