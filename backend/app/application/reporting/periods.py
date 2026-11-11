"""UC-TDB-02 — Périodes du tableau de bord, en journées de Douala (specs § 6.1, TR-07).

- Aujourd'hui, Hier ; Cette semaine = **lundi** → aujourd'hui ; Ce mois = le 1er → aujourd'hui ;
  Mois dernier = mois civil précédent entier ; Période libre = du … au … (inclus).
- `today` vient du port `Clock` (journée de Douala), jamais de l'heure du serveur.
- Période libre : `from` et `to` obligatoires, `from ≤ to ≤ aujourd'hui`, au plus
  `MAX_PERIOD_DAYS` jours (agrégats calculés à la demande, sans pré-calcul au Lot 1, § 10).
  Pour une autre période, `from` / `to` sont refusés (jamais ignorés en silence).
- Comparaison : la période **précédente de même longueur** (pour un jour : la veille).
"""

from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum

from app.domain.shared.errors import ValidationFailed

MAX_PERIOD_DAYS = 366


class PeriodKind(StrEnum):
    TODAY = "today"
    YESTERDAY = "yesterday"
    WEEK = "week"
    MONTH = "month"
    LAST_MONTH = "last_month"
    CUSTOM = "custom"


@dataclass(frozen=True, slots=True)
class Period:
    kind: PeriodKind
    first_day: date
    last_day: date

    def __post_init__(self) -> None:
        if self.last_day < self.first_day:
            msg = "Période inversée : « du » est après « au »"
            raise ValidationFailed(msg, details={"field": "from"})

    @property
    def days(self) -> int:
        return (self.last_day - self.first_day).days + 1

    def each_day(self) -> list[date]:
        return [self.first_day + timedelta(days=n) for n in range(self.days)]

    def previous(self) -> "Period":
        """Période de même longueur juste avant (la veille pour une journée)."""
        last = self.first_day - timedelta(days=1)
        return Period(self.kind, last - timedelta(days=self.days - 1), last)


def _first_of_previous_month(today: date) -> date:
    last_month_end = today.replace(day=1) - timedelta(days=1)
    return last_month_end.replace(day=1)


def resolve_period(
    kind: PeriodKind, today: date, first_day: date | None = None, last_day: date | None = None
) -> Period:
    """Bornes de la période demandée ; `ValidationFailed` (400) si elle est mal formée."""
    if kind is not PeriodKind.CUSTOM:
        if first_day is not None or last_day is not None:
            msg = "« du » / « au » ne vont qu'avec la période libre (period=custom)"
            raise ValidationFailed(msg, details={"field": "from"})
        return _named(kind, today)
    if first_day is None or last_day is None:
        msg = "La période libre exige « du » et « au »"
        raise ValidationFailed(msg, details={"field": "from" if first_day is None else "to"})
    if last_day > today:
        msg = "La période ne peut pas finir après aujourd'hui"
        raise ValidationFailed(msg, details={"field": "to", "max_date": today.isoformat()})
    period = Period(kind, first_day, last_day)
    if period.days > MAX_PERIOD_DAYS:
        msg = f"Période trop longue : {MAX_PERIOD_DAYS} jours au plus"
        raise ValidationFailed(msg, details={"field": "from", "max_days": MAX_PERIOD_DAYS})
    return period


def _named(kind: PeriodKind, today: date) -> Period:
    if kind is PeriodKind.TODAY:
        return Period(kind, today, today)
    if kind is PeriodKind.YESTERDAY:
        yesterday = today - timedelta(days=1)
        return Period(kind, yesterday, yesterday)
    if kind is PeriodKind.WEEK:
        return Period(kind, today - timedelta(days=today.weekday()), today)
    if kind is PeriodKind.MONTH:
        return Period(kind, today.replace(day=1), today)
    if kind is PeriodKind.LAST_MONTH:
        return Period(kind, _first_of_previous_month(today), today.replace(day=1) - timedelta(1))
    msg = f"Période non gérée : {kind}"  # CUSTOM est traité par l'appelant
    raise ValueError(msg)
