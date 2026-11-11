"""Réessai borné d'une transaction de créance sur course de concurrence (specs § 10).

Deux versements simultanés sur la même créance : le second à valider perd le verrou
optimiste (`VersionConflict`) ; une violation de `installment_number` est traitée de même.
La transaction **entière** est rejouée (lecture fraîche : le reste est recalculé, le second
versement peut alors recevoir `OVERPAYMENT`). Au-delà de `MAX_ATTEMPTS`, l'erreur remonte.
"""

from collections.abc import Callable

from app.application.receivables.ports import INSTALLMENT_NUMBER
from app.application.stock.retry import MAX_ATTEMPTS
from app.domain.shared.errors import Duplicate, VersionConflict


def is_receivable_race(error: VersionConflict | Duplicate) -> bool:
    if isinstance(error, VersionConflict):
        return True
    return error.details.get("constraint") == INSTALLMENT_NUMBER


def with_receivable_retry[T](action: Callable[[], T], attempts: int = MAX_ATTEMPTS) -> T:
    if attempts < 1:
        msg = "with_receivable_retry : au moins une tentative"
        raise ValueError(msg)
    for attempt in range(1, attempts + 1):
        try:
            return action()
        except (VersionConflict, Duplicate) as error:
            if not is_receivable_race(error) or attempt == attempts:
                raise
    msg = "with_receivable_retry : boucle terminée sans résultat"  # inatteignable
    raise AssertionError(msg)
