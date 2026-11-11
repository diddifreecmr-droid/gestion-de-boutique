"""UC-VEN-01 / UC-VEN-02 — Enregistrer une vente au comptant ou à crédit (SCN-01 étape 7).

Dans **une** transaction : numéro `V-000001` (RG-T05), lieu et vendeur (`resolver.py`), client
(création rapide comprise), lignes à instantanés et **coûts figés** (`lines.py`), paiements,
contrôles (prix minimum : avertissement par défaut, accord du propriétaire si le réglage
l'exige, `price_approval.py` ; plafond de crédit : `checks.py`), règles de paiement (`rules.py`),
châssis réservés (RG-M01), une « Sortie vente » par article (grand livre, RG-T17), journal.
Une vente à crédit publie `CreditSaleRecorded` (créance de T17) ; `remaining` est dans la vue.

- Date (`sold_on`, Q-46 tranchée) : facultative, aujourd'hui (Douala) par défaut ; RG-T09
  (vendeur J-7 inclus, propriétaire sans limite, jamais dans le futur).
- **Idempotent** (specs § 6.1, Q-37 tranchée) : un `sale_id` déjà connu renvoie la vente
  existante (`created=False`), **même si le contenu rejoué diffère**, sans second mouvement
  ni numéro consommé (comme les achats et les dépenses).
- Rejoué sur course de concurrence (`with_sale_retry`).
"""

from dataclasses import dataclass
from datetime import datetime

from app.application.expenses.references import checked_capture_time
from app.application.ports.clock import Clock
from app.application.ports.repository import not_found
from app.application.ports.uow import UnitOfWork, UnitOfWorkFactory
from app.application.sales import resolver as r
from app.application.sales.chassis_claims import sync_claims
from app.application.sales.checks import CustomerDebt, check_credit_limit
from app.application.sales.inputs import SaleInput
from app.application.sales.lines import resolve_line
from app.application.sales.ports import SaleRepository
from app.application.sales.price_approval import approve_minimums
from app.application.sales.retry import with_sale_retry
from app.application.sales.return_ports import PriceRequestRepository
from app.application.sales.stock_exits import post_exits
from app.application.sales.views import SaleView, view_of
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.security.roles import Role
from app.application.shops.context import actor_shop, performer_of
from app.application.shops.ports import ShopRepository, ShopSettingsRepository
from app.application.stock.ledger import StockLedger
from app.domain.profiles.registry import profile_for
from app.domain.purchasing.values import Capture
from app.domain.sales.ids import SaleId
from app.domain.sales.sale import Sale
from app.domain.sales.values import CreditTerms, SaleContent, SaleKind
from app.domain.shared.business_day import validate_entry_date
from app.domain.shared.doc_number import DocType, ProvisionalDocNumber
from app.domain.shared.errors import ValidationFailed


@dataclass(frozen=True, slots=True, kw_only=True)
class RecordSaleCommand:
    data: SaleInput
    sale_id: SaleId | None = None
    captured_at: datetime | None = None
    deferred: bool = False
    """Saisie hors connexion rejouée (RG-T18, T23) ; toujours faux en ligne."""
    provisional_number: ProvisionalDocNumber | None = None


class RecordSale:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        policy: Policy,
        ledger: StockLedger,
        clock: Clock,
        debt: CustomerDebt,
    ) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._ledger = ledger
        self._clock = clock
        self._debt = debt

    def execute(self, actor: Actor, command: RecordSaleCommand) -> tuple[SaleView, bool]:
        self._policy.require(actor, Permission.SALE_CREATE)
        return with_sale_retry(lambda: self._attempt(actor, command))

    def _attempt(self, actor: Actor, command: RecordSaleCommand) -> tuple[SaleView, bool]:
        now = self._clock.now()
        with self._uow_factory(actor_shop(actor)) as uow:
            sales = SaleRepository.within(uow)
            if command.sale_id is not None:
                existing = sales.find(command.sale_id)
                if existing is not None:
                    if actor.role is not Role.OWNER and existing.seller_id != actor.user_id:
                        raise not_found(command.sale_id)  # vente d'un autre vendeur
                    return view_of(self._policy, actor, existing), False
            _, view = self.record_in(uow, actor, command, now)
            uow.commit()
        return view, True

    def record_in(
        self, uow: UnitOfWork, actor: Actor, command: RecordSaleCommand, now: datetime
    ) -> tuple[Sale, SaleView]:
        """Vente neuve dans la transaction de l'appelant, **sans commit** (échange, UC-VEN-09)."""
        sale, view = self._build(uow, actor, command, now)
        # Sorties d'abord : en différé, elles posent `stock_to_verify` sur la vente (RG-T18),
        # qui doit être écrit avec elle (T23).
        post_exits(uow, self._ledger, sale, deferred=command.deferred)
        SaleRepository.within(uow).add(sale)
        sync_claims(uow, sale)
        return sale, view

    def _build(
        self, uow: UnitOfWork, actor: Actor, command: RecordSaleCommand, now: datetime
    ) -> tuple[Sale, SaleView]:
        data, today = command.data, self._clock.today()
        if data.kind is SaleKind.CASH and data.credit is not None:
            msg = "Conditions de crédit sur une vente au comptant"
            raise ValidationFailed(msg, details={"field": "credit"})
        sold_on = validate_entry_date(
            data.sold_on or today, today, is_owner=actor.role is Role.OWNER
        )
        settings = ShopSettingsRepository.within(uow).current().values
        profile = profile_for(ShopRepository.within(uow).current().profile_code.value)
        resolved = [resolve_line(uow, item, profile) for item in data.lines]
        below, request, warnings = approve_minimums(
            uow,
            resolved,
            enabled=settings.min_price_enabled,
            requires_approval=settings.min_price_requires_approval,
            actor=actor,
            request_id=data.price_request_id,
            now=now,
        )
        customer = r.sale_customer(uow, actor, data.customer, now)
        content = SaleContent(
            sold_on=sold_on,
            lines=tuple(line for line, _ in resolved),
            payments=r.sale_payments(uow, data.payments),
            customer_id=None if customer is None else customer.id,
            note=data.note,
        )
        sale = Sale(
            id=command.sale_id or SaleId.new(),
            shop_id=uow.shop_id,
            number=uow.numbering.next(DocType.SALE),
            kind=data.kind,
            location_id=r.sale_location(uow, actor, data.location_id),
            seller_id=r.sale_seller(uow, actor, data.seller_id),
            content=content,
            capture=Capture(
                created_by=actor.user_id,
                device_id=actor.device_id,
                captured_at=checked_capture_time(command.captured_at, now),
                received_at=now,
            ),
            credit=(data.credit or CreditTerms()) if data.kind is SaleKind.CREDIT else None,
            provisional_number=command.provisional_number,
        )
        sale.record(performer=performer_of(actor), below_minimum=below)
        if request is not None:
            request.use(sale.id, now)
            PriceRequestRepository.within(uow).update(request)
        if customer is not None and sale.kind is SaleKind.CREDIT:
            warnings += check_credit_limit(uow, self._debt, actor, customer, sale.remaining)
        return sale, view_of(self._policy, actor, sale, warnings=tuple(warnings))
