"""Réponses du Tableau de bord et des accueils (UC-TDB-01 à 05, specs § 6.3).

Montants en entiers FCFA ; pourcentages en chaînes décimales à 2 chiffres (`"28.57"`, jamais
de flottant) ; `null` = non calculable (variation sur une période précédente à 0, taux sans
ventes, valeur de stock avec un article sans coût, RG-T15). Un bloc du Lot 2 est un objet
`NotAvailable` explicite, jamais un 0.

**Module éteint pour la boutique** (specs § 15.1) : son bloc vaut `null` — `summary.expenses`
(`expenses` ; le résultat simple est alors la marge), `receivables` (`receivables`),
`stock.in_transit` (`transfers`), `trucks` (`transport`) ; dans les accueils,
`seller.reminders_due`, `accountant.expenses`, `accountant.transfers_to_receive`, les blocs du
chauffeur. Aucun 0 trompeur.
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.interface.http.schemas.stock import Valuation


class _Out(BaseModel):
    model_config = ConfigDict(frozen=True)


class NotAvailable(_Out):
    available: Literal[False]
    lot: int
    message: str


class PeriodOut(_Out):
    kind: str
    first_day: date
    last_day: date
    days: int


class Compared(_Out):
    value: int
    previous: int
    change_pct: str | None
    """(valeur - précédente) / |précédente| x 100 ; `null` si la précédente vaut 0."""


class Summary(_Out):
    sales: Compared
    sales_count: Compared
    collected: Compared
    margin: Compared
    margin_wac: Compared
    margin_gap: int
    """Marge au CMP - marge au dernier coût (UC-TDB-03)."""
    margin_rate_pct: str | None
    without_cost: int
    """« N ventes sans coût connu » : lignes à marge non calculable (RG-T15)."""
    expenses: Compared | None
    """`null` : module `expenses` éteint (aucune dépense dans les chiffres)."""
    result: Compared


class SeriesPoint(_Out):
    day: date
    sales: int
    margin: int


class Series(_Out):
    points: list[SeriesPoint]
    total_sales: int
    total_margin: int
    average_sales: int
    average_margin: int


class ReceivablesBlock(_Out):
    total_due: int
    debtor_count: int
    received: Compared
    reminders_due: int


class StockBlock(_Out):
    value: Valuation
    damaged: Valuation
    low_stock: int
    to_verify: int
    in_transit: NotAvailable | None


class AlertsBlock(_Out):
    error_reports: int
    price_requests: int


class TrucksBlock(_Out):
    trucks: NotAvailable
    transport_expenses: NotAvailable


class DashboardResponse(_Out):
    period: PeriodOut
    previous_period: PeriodOut
    summary: Summary
    series: Series | None
    receivables: ReceivablesBlock | None
    stock: StockBlock
    trucks: TrucksBlock | None
    alerts: AlertsBlock


class DetailLineOut(_Out):
    kind: str
    id: str
    label: str
    day: date | None = None
    amount: int | None = None
    count: int | None = None
    margin: int | None = None
    quantity: str | None = None
    threshold: str | None = None


class DashboardDetailResponse(_Out):
    metric: str
    period: PeriodOut
    total: int
    lines: list[DetailLineOut]


class SellerHomeOut(_Out):
    sales_count: int
    sales_amount: int
    reminders_due: int | None
    pending_uploads: int


class AccountantHomeOut(_Out):
    transfers_to_receive: NotAvailable | None
    low_stock: int
    stock_value: Valuation
    expenses: int | None


class DriverHomeOut(_Out):
    current_trip: NotAvailable | None
    trip_expenses: NotAvailable | None


class HomeResponse(_Out):
    """Un seul bloc rempli, celui du rôle ; les autres sont absents de la réponse."""

    role: str
    today: date
    owner: DashboardResponse | None = None
    seller: SellerHomeOut | None = None
    accountant: AccountantHomeOut | None = None
    driver: DriverHomeOut | None = None
