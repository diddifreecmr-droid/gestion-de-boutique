"""Cas d'utilisation employés par la démonstration, et l'horloge rejouée qui les date.

`ReplayClock` : l'horloge **injectée** dans le noyau (`build_core`) à la place de l'horloge
système. Les cas d'utilisation (achats, ventes, dépenses) datent leurs écritures par
`clock.now()` / `clock.today()` ; la démonstration recule l'horloge avant chaque action
(`at`) pour obtenir un historique sur les 7 derniers jours, sans toucher aux règles métier.
Elle ne revient jamais au-delà de l'instant réel de départ.

`KnownPins` : générateur de codes provisoires qui remet le code **connu** prévu pour le compte
(`expect`), affiché à la fin ; le compte reste « à changer à la 1re connexion ».
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.application.identity.ports import TemporaryPinGenerator
from app.application.ports.clock import Clock
from app.bootstrap.catalog import build_catalog
from app.bootstrap.expenses import build_expenses
from app.bootstrap.identity import IdentityModule
from app.bootstrap.purchasing import build_purchasing
from app.bootstrap.sales import build_sales
from app.bootstrap.shops import build_shops
from app.bootstrap.stock import build_stock
from app.interface.http.routes.catalog import CatalogComponents
from app.interface.http.routes.expense_components import ExpensesComponents
from app.interface.http.routes.purchasing_components import PurchasingComponents
from app.interface.http.routes.sales_components import SalesComponents
from app.interface.http.routes.shop_components import ShopsComponents


class ReplayClock(Clock):
    def __init__(self, start: datetime) -> None:
        if start.tzinfo is None:
            msg = "ReplayClock : instant de départ naïf (UTC attendu)"
            raise ValueError(msg)
        self.start = start
        self._now = start

    def now(self) -> datetime:
        return self._now

    def at(self, days_ago: int, hours_ago: float = 0) -> None:
        """Place l'horloge `days_ago` jours et `hours_ago` heures avant l'instant de départ."""
        if days_ago < 0 or hours_ago < 0:
            msg = "ReplayClock : la démonstration ne date rien dans le futur"
            raise ValueError(msg)
        self._now = self.start - timedelta(days=days_ago, hours=hours_ago)

    def reset(self) -> None:
        self._now = self.start


class KnownPins(TemporaryPinGenerator):
    def __init__(self) -> None:
        self._next: str | None = None

    def expect(self, pin: str) -> None:
        self._next = pin

    def generate(self) -> str:
        pin, self._next = self._next, None
        if pin is None:
            msg = "Code provisoire de démonstration non préparé (ou refusé comme trop simple)"
            raise RuntimeError(msg)
        return pin


@dataclass(frozen=True, slots=True, kw_only=True)
class DemoServices:
    identity: IdentityModule
    clock: ReplayClock
    pins: KnownPins
    shops: ShopsComponents
    catalog: CatalogComponents
    purchasing: PurchasingComponents
    sales: SalesComponents
    expenses: ExpensesComponents


def build_services(identity: IdentityModule) -> DemoServices:
    clock = identity.clock
    if not isinstance(clock, ReplayClock):
        msg = "seed_demo : le noyau doit être assemblé avec une ReplayClock (build_core)"
        raise TypeError(msg)
    pins = KnownPins()
    stock = build_stock(identity)
    return DemoServices(
        identity=identity,
        clock=clock,
        pins=pins,
        shops=build_shops(identity, pins=pins).http,
        catalog=build_catalog(identity).http,
        purchasing=build_purchasing(identity, stock.ledger).http,
        sales=build_sales(identity, stock.ledger).http,
        expenses=build_expenses(identity).http,
    )
