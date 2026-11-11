"""UC-VEN-07 — Modifier une vente (propriétaire, `SALE_UPDATE` ; recette MOD-01 à MOD-03).

`PATCH` + `version` + motif obligatoire. Modifiables : prix vendu et détails de chaque ligne,
client, paiements, date, note. **Changer l'article ou la quantité est refusé**
(`LINE_CHANGE_NOT_ALLOWED` : retour ou annulation puis nouvelle vente). Les marges sont
recalculées avec les **mêmes coûts figés** (MOD-01 : 780 000 → 760 000, marge 240 000 →
220 000) ; une vente à crédit publie `CreditSaleAmountsChanged` (créance 480 000 → 460 000,
T17). Les règles de paiement restent celles de la création (comptant payé en entier, payé ≤
total : baisser un prix sous le déjà-payé exige d'ajuster les paiements, MOD-03).
Changer la date ne déplace pas les mouvements de stock (Q-06 ouverte) ; châssis resynchronisés.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from decimal import Decimal
from typing import Any

from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWork, UnitOfWorkFactory
from app.application.sales import resolver as r
from app.application.sales.chassis_claims import sync_claims
from app.application.sales.lines import check_details
from app.application.sales.ports import SaleRepository
from app.application.sales.retry import with_sale_retry
from app.application.sales.views import SaleView, view_of
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop, performer_of, require_version
from app.application.shops.ports import ShopRepository
from app.domain.catalog.ids import ArticleId
from app.domain.profiles.registry import profile_for
from app.domain.sales.errors import LineChangeRefused
from app.domain.sales.ids import SaleId
from app.domain.sales.lines import SaleLine, SoldDetail
from app.domain.sales.sale import Sale
from app.domain.sales.values import SaleContent
from app.domain.shared.business_day import validate_entry_date
from app.domain.shared.money import Money

PATCHABLE = frozenset({"lines", "payments", "customer", "sold_on", "note"})


@dataclass(frozen=True, slots=True, kw_only=True)
class LinePatch:
    unit_price: int | None = None
    details: tuple[SoldDetail, ...] | None = None
    article_id: ArticleId | None = None
    """Facultatif : s'il est donné, il doit être celui de la ligne (sinon refus)."""
    quantity: Decimal | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class ModifySaleCommand:
    sale_id: SaleId
    version: int
    reason: str
    patch: Mapping[str, Any] = field(default_factory=dict)


def patched_line(line: SaleLine, change: LinePatch) -> SaleLine:
    if change.article_id is not None and change.article_id != line.article_id:
        raise LineChangeRefused("lines.article_id")
    if change.quantity is not None and change.quantity != line.quantity:
        raise LineChangeRefused("lines.quantity")
    if change.unit_price is not None:
        line = line.repriced(Money.entry(change.unit_price, "lines.unit_price"))
    return line if change.details is None else line.with_details(change.details)


class ModifySale:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock

    def execute(self, actor: Actor, command: ModifySaleCommand) -> SaleView:
        unknown = set(command.patch) - PATCHABLE
        if unknown:
            msg = f"Champs non modifiables : {sorted(unknown)}"
            raise ValueError(msg)
        self._policy.require(actor, Permission.SALE_UPDATE)  # avant toute lecture
        return with_sale_retry(lambda: self._attempt(actor, command))

    def _attempt(self, actor: Actor, command: ModifySaleCommand) -> SaleView:
        now = self._clock.now()
        with self._uow_factory(actor_shop(actor)) as uow:
            sales = SaleRepository.within(uow)
            sale = sales.get(command.sale_id)
            sale.require_valid()
            require_version(sale.version, command.version)
            content = self._content(uow, actor, sale, command.patch)
            if sale.modify(content, reason=command.reason, performer=performer_of(actor), now=now):
                sales.update(sale)
                sync_claims(uow, sale)
                uow.commit()
        return view_of(self._policy, actor, sale)

    def _content(
        self, uow: UnitOfWork, actor: Actor, sale: Sale, patch: Mapping[str, Any]
    ) -> SaleContent:
        content = sale.content
        changes: dict[str, Any] = {}
        if "lines" in patch:
            wanted: tuple[LinePatch, ...] = patch["lines"]
            if len(wanted) != len(content.lines):
                raise LineChangeRefused("lines")
            profile = profile_for(ShopRepository.within(uow).current().profile_code.value)
            for change in wanted:
                if change.details is not None:
                    check_details(change.details, profile)
            changes["lines"] = tuple(
                patched_line(line, change)
                for line, change in zip(content.lines, wanted, strict=True)
            )
        if "payments" in patch:
            changes["payments"] = r.sale_payments(uow, patch["payments"])
        if "customer" in patch:
            customer = r.sale_customer(uow, actor, patch["customer"], self._clock.now())
            changes["customer_id"] = None if customer is None else customer.id
        if "sold_on" in patch and patch["sold_on"] is not None:
            today = self._clock.today()
            changes["sold_on"] = validate_entry_date(patch["sold_on"], today, is_owner=True)
        if "note" in patch:
            changes["note"] = patch["note"]
        return replace(content, **changes)
