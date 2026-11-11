"""Règles d'alerte du stock, branchées sur l'`AlertDispatcher` (T09) par la composition root.

- Stock bas (UC-STK-09) : `StockTotalChanged` dont le stock vendable tous lieux passe
  **strictement** sous le seuil (Q-18) → propriétaires et comptables actifs, une seule fois
  (`low_stock:<article>`) ; résolue dès que le stock revient au seuil ou au-dessus.
- Stock à vérifier (RG-T18) : `StockBecameNegative` → propriétaires et comptables, à chaque cas.
- Ajustement (ADJ-03) : `AdjustmentRecorded` par un comptable, hors inventaire → propriétaires.
- Inventaire validé (INV-04) : `InventoryValidated` + valeur des écarts → propriétaires.
"""

from collections.abc import Iterable

from app.application.alerts.dispatcher import (
    AlertDirective,
    AlertDispatcher,
    AlertNotice,
    AlertResolution,
)
from app.application.ports.uow import UnitOfWork
from app.application.shops.ports import MembershipRepository
from app.domain.alerts.alert import AlertType
from app.domain.audit.values import EntityRef
from app.domain.shared.ids import UserId
from app.domain.shared.roles import Role
from app.domain.stock.events import (
    AdjustmentRecorded,
    InventoryValidated,
    StockBecameNegative,
    StockTotalChanged,
)

STOCK_WATCHERS = frozenset({Role.OWNER, Role.ACCOUNTANT})
OWNERS = frozenset({Role.OWNER})


def recipients(uow: UnitOfWork, roles: frozenset[Role]) -> list[UserId]:
    members = MembershipRepository.within(uow).list_all()
    return [m.user_id for m in members if m.active and m.role in roles]


def low_stock_key(event: StockTotalChanged) -> str:
    return f"low_stock:{event.article_id}"


def low_stock(event: StockTotalChanged, uow: UnitOfWork) -> Iterable[AlertDirective]:
    key = low_stock_key(event)
    if event.after >= event.threshold:
        return [AlertResolution(key)]
    message = f"Stock bas : {event.article_name} — {event.after} en stock (seuil {event.threshold})"
    return [
        AlertNotice(
            recipients=recipients(uow, STOCK_WATCHERS),
            type=AlertType.LOW_STOCK,
            entity=EntityRef("article", event.article_id.value, event.article_name[:500]),
            message=message[:500],
            dedup_key=key,
        )
    ]


def stock_to_verify(event: StockBecameNegative, uow: UnitOfWork) -> Iterable[AlertDirective]:
    message = (
        f"Stock à vérifier : {event.article_name} à {event.location_name} "
        f"({event.balance} après une vente différée)"
    )
    return [
        AlertNotice(
            recipients=recipients(uow, STOCK_WATCHERS),
            type=AlertType.STOCK_TO_VERIFY,
            entity=EntityRef("article", event.article_id.value, event.article_name[:500]),
            message=message[:500],
        )
    ]


def adjustment_by_accountant(
    event: AdjustmentRecorded, uow: UnitOfWork
) -> Iterable[AlertDirective]:
    if event.from_inventory or event.performer.role != Role.ACCOUNTANT.value:
        return []
    return [
        AlertNotice(
            recipients=recipients(uow, OWNERS),
            type=AlertType.STOCK_ADJUSTMENT,
            entity=event.entity,
            message=f"{event.summary} (par le comptable)"[:500],
        )
    ]


def inventory_validated(event: InventoryValidated, uow: UnitOfWork) -> Iterable[AlertDirective]:
    value = "non calculable" if event.gap_value is None else str(event.gap_value)
    message = f"{event.summary} — valeur totale des écarts : {value}"
    return [
        AlertNotice(
            recipients=recipients(uow, OWNERS),
            type=AlertType.INVENTORY_VALIDATED,
            entity=event.entity,
            message=message[:500],
        )
    ]


def register_stock_alerts(dispatcher: AlertDispatcher) -> None:
    """À appeler **une fois** par répartiteur (composition root, `bootstrap/core.py`)."""
    dispatcher.register(StockTotalChanged, low_stock)
    dispatcher.register(StockBecameNegative, stock_to_verify)
    dispatcher.register(AdjustmentRecorded, adjustment_by_accountant)
    dispatcher.register(InventoryValidated, inventory_validated)
