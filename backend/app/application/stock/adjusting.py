"""Enregistrer un ajustement **et** son mouvement dans la même transaction (UC-STK-08, UC-STK-07).

Partagé par l'ajustement ponctuel et la validation d'un inventaire (un ajustement par écart).
Le mouvement est posté par le grand livre (en ligne : un ajustement - supérieur au stock est
refusé, ADJ-04). Coût d'un ajustement + (décision Q-16) : le **CMP courant** de l'article s'il
est connu, sinon aucun ; l'ajustement ne modifie jamais le CMP (RG-T12).
"""

from dataclasses import dataclass
from datetime import datetime

from app.application.catalog.ports import ArticleRepository
from app.application.ports.uow import UnitOfWork
from app.application.stock.ledger import StockLedger
from app.application.stock.ports import AdjustmentRepository
from app.application.stock.postings import Posting
from app.domain.audit.values import Performer
from app.domain.shared.doc_number import DocNumber
from app.domain.stock.adjustment import Adjustment, AdjustmentDirection, AdjustmentDraft
from app.domain.stock.movement import StockMovement
from app.domain.stock.values import SourceRef, SourceType


@dataclass(frozen=True, slots=True)
class AdjustmentResult:
    adjustment: Adjustment
    movement: StockMovement | None
    """`None` pour un rejeu idempotent (le mouvement d'origine reste dans le grand livre)."""


def post_adjustment(
    uow: UnitOfWork,
    ledger: StockLedger,
    draft: AdjustmentDraft,
    *,
    performer: Performer,
    now: datetime,
    inventory_number: DocNumber | None = None,
) -> AdjustmentResult:
    article = ArticleRepository.within(uow).get(draft.article_id)
    adjustment = Adjustment.record(
        draft,
        shop_id=uow.shop_id,
        performer=performer,
        now=now,
        article_name=article.display_name,
    )
    AdjustmentRepository.within(uow).add(adjustment)
    if adjustment.inventory_id is not None and inventory_number is not None:
        source = SourceRef(
            SourceType.INVENTORY, adjustment.inventory_id.value, str(inventory_number)
        )
    else:
        source = SourceRef(SourceType.ADJUSTMENT, adjustment.id.value)
    entering = adjustment.direction is AdjustmentDirection.IN
    posting = Posting(
        article_id=article.id,
        location_id=adjustment.location_id,
        type=adjustment.movement_type,
        quantity=adjustment.quantity,
        source=source,
        occurred_at=now,
        author_id=performer.user_id,
        condition=adjustment.condition,
        unit_cost=article.wac if entering else None,
    )
    record = ledger.record_entry if entering else ledger.record_exit
    movement = record(uow, posting)
    return AdjustmentResult(adjustment, movement)
