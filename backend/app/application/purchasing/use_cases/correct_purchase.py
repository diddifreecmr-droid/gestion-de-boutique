"""UC-ACH-03 — Corriger un achat (`PATCH` + `version` + motif ; recette SCN-04, PUR-06 à PUR-08).

- Droits : comptable jusqu'à J+7 inclus après la date d'achat, propriétaire toujours
  (`CORRECTION_WINDOW_CLOSED`, 422) ; motif obligatoire (`REASON_REQUIRED`, 400).
- Champs absents du `patch` : inchangés ; présents : revérifiés comme à la saisie. Le numéro,
  l'auteur et la capture ne changent jamais ; avant/après champ par champ au journal.
- **Stock et CMP comme si l'achat avait été saisi juste dès le départ** : si le lieu, la date
  ou une quantité / un coût de ligne change, les anciennes entrées sont annulées et les
  nouvelles posées à la **même date d'opération** (date d'achat), puis le CMP et le dernier
  coût de chaque article touché sont rejoués sur le stock réel (`refresh_costs`, Q-02).
- Refus (`STOCK_ALREADY_LEFT`) si la nouvelle quantité d'un article au lieu est inférieure à ce
  qui en est déjà sorti (`require_kept`, PUR-06) : il faut passer par un ajustement.
- Les ventes passées gardent leurs coûts figés (RG-T13) : rien à réécrire ici.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field, fields, replace
from datetime import datetime
from typing import Any

from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWork, UnitOfWorkFactory
from app.application.purchasing.costs import refresh_costs, replay_article
from app.application.purchasing.entries import (
    live_entries,
    post_entries,
    require_kept,
    reverse_entries,
)
from app.application.purchasing.ports import PurchaseRepository
from app.application.purchasing.price_gap import require_confirmed
from app.application.purchasing.resolver import FeeInput, LineInput, PurchaseInput, PurchaseResolver
from app.application.purchasing.views import PurchaseView, view_of
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.security.roles import Role
from app.application.shops.context import actor_shop, performer_of, require_version
from app.application.stock.ledger import StockLedger
from app.application.stock.retry import with_stock_retry
from app.domain.purchasing.ids import PurchaseId
from app.domain.purchasing.purchase import Purchase
from app.domain.stock.movement import StockMovement

PATCHABLE = frozenset(f.name for f in fields(PurchaseInput))


@dataclass(frozen=True, slots=True, kw_only=True)
class CorrectPurchaseCommand:
    purchase_id: PurchaseId
    version: int
    reason: str
    patch: Mapping[str, Any] = field(default_factory=dict)
    confirm_price_gap: bool = False


def input_of(purchase: Purchase) -> PurchaseInput:
    """Saisie équivalente à l'achat enregistré (point de départ d'un `patch`)."""
    details = purchase.details
    return PurchaseInput(
        lines=tuple(
            LineInput(
                article_id=line.article_id,
                quantity=line.quantity,
                unit_price=line.unit_price.amount,
                unit=line.unit,
            )
            for line in details.lines
        ),
        fees=tuple(
            FeeInput(kind=f.kind, amount=f.amount.amount, label=f.label) for f in details.fees
        ),
        purchase_date=details.purchase_date,
        location_id=details.location_id,
        supplier_id=details.supplier_id,
        invoice_ref=details.invoice_ref,
        invoice_photo_id=details.invoice_photo_id,
        note=details.note,
    )


def stock_key(purchase: Purchase) -> tuple[object, ...]:
    """Ce qui détermine les entrées de stock : lieu, date d'opération, quantités et coûts."""
    lines = tuple((c.line.article_id, c.stock_quantity, c.unit_cost) for c in purchase.costed)
    return (purchase.details.location_id, purchase.entry_instant, lines)


class CorrectPurchase:
    def __init__(
        self, uow_factory: UnitOfWorkFactory, policy: Policy, ledger: StockLedger, clock: Clock
    ) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._ledger = ledger
        self._clock = clock

    def execute(self, actor: Actor, command: CorrectPurchaseCommand) -> PurchaseView:
        unknown = set(command.patch) - PATCHABLE
        if unknown:
            msg = f"Champs non modifiables : {sorted(unknown)}"
            raise ValueError(msg)
        self._policy.require(actor, Permission.PURCHASE_WRITE)  # avant toute lecture
        return with_stock_retry(lambda: self._attempt(actor, command))

    def _attempt(self, actor: Actor, command: CorrectPurchaseCommand) -> PurchaseView:
        now, today = self._clock.now(), self._clock.today()
        is_owner = actor.role is Role.OWNER
        with self._uow_factory(actor_shop(actor)) as uow:
            purchases = PurchaseRepository.within(uow)
            purchase = purchases.get(command.purchase_id)
            purchase.require_correctable(by_owner=is_owner, today=today)
            require_version(purchase.version, command.version)
            resolver = PurchaseResolver(uow, today=today, is_owner=is_owner, previous=purchase)
            data = replace(input_of(purchase), **command.patch)
            details, costed = resolver.resolve(data)
            previous_lines = {line.line for line in purchase.costed}
            before = stock_key(purchase)
            old_articles = [line.article_id for line in purchase.details.lines]
            require_confirmed(
                ((i, line) for i, line in enumerate(costed) if line.line not in previous_lines),
                lambda article_id: (
                    replay_article(uow, article_id, exclude_source=purchase.id.value).last_cost
                ),
                confirmed=command.confirm_price_gap,
            )
            entries = live_entries(uow, purchase.id)
            performer = performer_of(actor)
            if not purchase.correct(
                details, costed, reason=command.reason, performer=performer, now=now
            ):
                return view_of(actor, purchase, today)
            purchases.update(purchase)
            if stock_key(purchase) != before:
                self._restock(uow, purchase, entries, actor, now)
                refresh_costs(uow, [*old_articles, *(line.article_id for line in details.lines)])
            uow.commit()
        return view_of(actor, purchase, today)

    def _restock(
        self,
        uow: UnitOfWork,
        purchase: Purchase,
        entries: list[StockMovement],
        actor: Actor,
        now: datetime,
    ) -> None:
        location = purchase.details.location_id
        kept = {(c.line.article_id, location): c.stock_quantity for c in purchase.costed}
        require_kept(uow, entries, kept)
        post_entries(uow, self._ledger, purchase, actor.user_id)
        reverse_entries(uow, self._ledger, purchase, entries, author_id=actor.user_id, now=now)
