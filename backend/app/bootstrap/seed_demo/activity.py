"""Vie d'une boutique de démonstration, datée par la `ReplayClock` (J-10 → aujourd'hui).

- J-10 : fournisseurs et articles (gérant).
- J-9 : stock initial = un achat reçu avec ses coûts (`RecordPurchase`, CMP et dernier coût
  tenus par les Achats) ; J-8 et J-4 : deux réassorts.
- J-6 → J-0 : 12 ventes réparties entre les deux employés, une à crédit si le module Créances
  est actif (la créance naît avec la vente, `ReceivableSync`).
- Deux dépenses (gérant).
"""

from datetime import timedelta

from app.application.expenses.references import ExpenseInput
from app.application.expenses.use_cases.record_expense import RecordExpenseCommand
from app.application.purchasing.resolver import LineInput as PurchaseLine
from app.application.purchasing.resolver import PurchaseInput
from app.application.purchasing.use_cases.record_purchase import RecordPurchaseCommand
from app.application.sales.inputs import CustomerInput, LineInput, PaymentInput, SaleInput
from app.application.sales.use_cases.record_sale import RecordSaleCommand
from app.application.security.actor import Actor
from app.bootstrap.seed_demo.opening import OpenedDemo
from app.bootstrap.seed_demo.plan import ShopPlan, StockedItem
from app.bootstrap.seed_demo.services import DemoServices
from app.domain.profiles.modules import Module
from app.domain.purchasing.ids import SupplierId
from app.domain.purchasing.supplier import SupplierDetails
from app.domain.sales.values import CreditTerms, SaleKind

SALES_COUNT = 12
CREDIT_SALE = 5
"""Rang de la vente à crédit (si le module Créances est actif)."""


def run_activity(services: DemoServices, plan: ShopPlan, shop: OpenedDemo) -> int:
    """Déroule la vie de la boutique ; renvoie le nombre de ventes enregistrées."""
    clock, owner = services.clock, shop.owner
    clock.at(10)
    suppliers = [
        services.purchasing.suppliers.create(owner, SupplierDetails(name=name, city=plan.city))[0]
        for name in plan.suppliers
    ]
    items = plan.catalog(services.catalog, owner)
    _purchase(services, shop, suppliers[0].id, items, 9, opening=True)
    _purchase(services, shop, suppliers[1].id, items[:3], 8)
    _purchase(services, shop, suppliers[-1].id, items[3:6], 4)
    credit = _receivables_enabled(services, shop)
    for rank in range(SALES_COUNT):
        _sale(services, plan, shop, items, rank, credit=credit and rank == CREDIT_SALE)
    _expenses(services, plan, owner)
    clock.reset()
    return SALES_COUNT


def _purchase(
    services: DemoServices,
    shop: OpenedDemo,
    supplier: SupplierId,
    items: list[StockedItem],
    days_ago: int,
    *,
    opening: bool = False,
) -> None:
    services.clock.at(days_ago, hours_ago=2)
    lines = tuple(
        PurchaseLine(
            article_id=item.article_id,
            quantity=item.opening if opening else item.restock,
            unit_price=item.unit_cost,
            unit=item.entry_unit,
        )
        for item in items
    )
    note = "Stock initial (démonstration)" if opening else "Réassort (démonstration)"
    data = PurchaseInput(lines=lines, location_id=shop.store_id, supplier_id=supplier, note=note)
    services.purchasing.record.execute(
        shop.owner, RecordPurchaseCommand(data=data, confirm_price_gap=True)
    )


def _receivables_enabled(services: DemoServices, shop: OpenedDemo) -> bool:
    summary = services.identity.core.catalog.find(shop.shop_id)
    if summary is None:
        msg = f"Boutique {shop.shop_id} absente du catalogue plateforme"
        raise RuntimeError(msg)
    return Module.RECEIVABLES in summary.enabled_modules


def _cash_mode(services: DemoServices, actor: Actor) -> PaymentInput:
    modes = services.shops.payment_modes.list(actor)
    for mode in modes:
        if mode.name == "Espèces":
            return PaymentInput(mode_id=mode.id, amount=0)
    msg = "Mode de paiement « Espèces » introuvable"
    raise RuntimeError(msg)


def _sale(
    services: DemoServices,
    plan: ShopPlan,
    shop: OpenedDemo,
    items: list[StockedItem],
    rank: int,
    *,
    credit: bool,
) -> None:
    days_ago = 6 - (rank * 7) // SALES_COUNT
    services.clock.at(days_ago, hours_ago=1 + rank % 4)
    seller = shop.sellers[rank % 2]
    item = items[(rank * 5) % len(items)]
    option = item.sales[(rank // 2) % len(item.sales)]
    line = LineInput(
        article_id=item.article_id,
        quantity=option.quantity,
        unit_price=option.unit_price,
        sale_mode=option.mode,
    )
    cash = _cash_mode(services, seller)
    paid = option.amount // 3 if credit else option.amount
    data = SaleInput(
        kind=SaleKind.CREDIT if credit else SaleKind.CASH,
        lines=(line,),
        payments=(PaymentInput(mode_id=cash.mode_id, amount=paid),),
        location_id=shop.store_id,
        customer=CustomerInput(name=plan.customer[0], phone=plan.customer[1]) if credit else None,
        credit=CreditTerms(
            reminder_on=services.clock.today() + timedelta(days=14), terms="Solde en 2 versements"
        )
        if credit
        else None,
    )
    services.sales.record.execute(seller, RecordSaleCommand(data=data))


def _expenses(services: DemoServices, plan: ShopPlan, owner: Actor) -> None:
    categories = {c.name: c.id for c in services.expenses.categories.list(owner)}
    cash = _cash_mode(services, owner)
    for expense in plan.expenses:
        services.clock.at(expense.days_ago, hours_ago=3)
        category = categories.get(expense.category)
        if category is None:
            msg = f"Catégorie de dépense « {expense.category} » introuvable"
            raise RuntimeError(msg)
        data = ExpenseInput(
            amount=expense.amount,
            category_id=category,
            payment_mode_id=cash.mode_id,
            description=expense.description,
            location_id=None,
        )
        services.expenses.record.execute(owner, RecordExpenseCommand(data=data))
