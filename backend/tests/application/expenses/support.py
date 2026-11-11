"""Monde de test des dépenses : « Motos Garoua » ouverte, propriétaire, comptable, vendeur.

Noyau mémoire réel (journal et alertes branchés), horloge figée (`World.clock`).
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.application.expenses.references import ExpenseInput
from app.application.expenses.use_cases.list_expenses import ExpenseCriteria, ExpenseListing
from app.application.expenses.use_cases.record_expense import RecordExpenseCommand
from app.application.expenses.views import ExpenseView
from app.application.ports.pagination import PageRequest
from app.application.security.actor import Actor
from app.bootstrap.expenses import build_expenses
from app.domain.shared.roles import Role
from app.domain.shops.ids import ExpenseCategoryId, PaymentModeId
from app.interface.http.routes.expense_components import ExpensesComponents
from tests.application.shops.support import World

ACCOUNTANT_PHONE = "677000003"
SELLER_PHONE = "677000002"
DRIVER_PHONE = "677000004"


@dataclass
class Shop:
    world: World = field(default_factory=World)

    def __post_init__(self) -> None:
        opened = self.world.open_motos()
        self.owner: Actor = self.world.owner(opened)
        self.accountant = self.world.member(self.owner, ACCOUNTANT_PHONE, Role.ACCOUNTANT)
        self.seller = self.world.member(self.owner, SELLER_PHONE, Role.SELLER, "Garoua")
        self.driver = self.world.member(self.owner, DRIVER_PHONE, Role.DRIVER)
        self.uc: ExpensesComponents = build_expenses(self.world.identity).http

    def category(self, name: str) -> ExpenseCategoryId:
        return next(c.id for c in self.uc.categories.list(self.owner) if c.name == name)

    def mode(self, name: str) -> PaymentModeId:
        modes = self.world.http.payment_modes.list(self.owner)
        return next(m.id for m in modes if m.name == name)

    def record(
        self, actor: Actor, amount: int = 25_000, category: str = "Carburant", **extra: Any
    ) -> ExpenseView:
        command_fields = {k: extra.pop(k) for k in ("expense_id", "captured_at") if k in extra}
        data = ExpenseInput(amount=amount, category_id=self.category(category), **extra)
        view, _ = self.uc.record.execute(actor, RecordExpenseCommand(data=data, **command_fields))
        return view

    def listing(
        self, actor: Actor | None = None, limit: int = 50, **criteria: Any
    ) -> ExpenseListing:
        return self.uc.list.execute(
            actor or self.owner, ExpenseCriteria(**criteria), PageRequest(limit=limit)
        )

    def day(self, first: date, last: date | None = None) -> ExpenseListing:
        return self.listing(first_day=first, last_day=last or first)
