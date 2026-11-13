"""Délai d'échange `exchange_days` (UC-PAP-01, décision client QC-4 du 2026-11-13, T29).

- Délai **inclusif**, compté en journées (Douala) depuis la journée de la vente : vente du 1er,
  délai 7 → échange possible jusqu'au 8 inclus ; le 9, il est hors délai. Délai 0 = le jour
  même. Délai absent (`None`) = aucune limite.
- L'employé hors délai → `ExchangePeriodOver` (422 `EXCHANGE_PERIOD_OVER`, `details` :
  `sold_on`, `exchange_days`, `deadline`).
- Le propriétaire **peut dépasser** le délai : `check_exchange_period` renvoie alors `True`
  (« hors délai ») et l'échange est inscrit au journal comme action sensible
  (`SaleExchangedLate`).
"""

from datetime import date, timedelta

from app.domain.shared.errors import DomainError


class ExchangePeriodOver(DomainError):
    code = "EXCHANGE_PERIOD_OVER"

    def __init__(self, *, sold_on: date, exchange_days: int, deadline: date) -> None:
        super().__init__(
            "Délai d'échange dépassé : seul le propriétaire peut encore échanger cette vente",
            details={
                "sold_on": sold_on.isoformat(),
                "exchange_days": exchange_days,
                "deadline": deadline.isoformat(),
            },
        )


def exchange_deadline(sold_on: date, exchange_days: int | None) -> date | None:
    """Dernière journée où l'échange est dans le délai ; `None` = pas de délai."""
    if exchange_days is None:
        return None
    if isinstance(exchange_days, bool) or not isinstance(exchange_days, int) or exchange_days < 0:
        msg = f"exchange_days doit être un entier ≥ 0, reçu {exchange_days!r}"
        raise ValueError(msg)
    return sold_on + timedelta(days=exchange_days)


def check_exchange_period(
    sold_on: date, today: date, exchange_days: int | None, *, may_exceed: bool
) -> bool:
    """`True` si l'échange est hors délai (permis seulement si `may_exceed`), sinon `False`."""
    deadline = exchange_deadline(sold_on, exchange_days)
    if deadline is None or today <= deadline:
        return False
    if not may_exceed:
        days = (deadline - sold_on).days
        raise ExchangePeriodOver(sold_on=sold_on, exchange_days=days, deadline=deadline)
    return True
