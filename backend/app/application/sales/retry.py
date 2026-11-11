"""Réessai borné d'une transaction de vente sur course de concurrence (ERR-STK-05, RG-M01).

Rejoue la transaction **entière** (lecture fraîche) au plus `MAX_ATTEMPTS` fois quand elle a
perdu une course : projection de stock (`with_stock_retry`), numéro, châssis réservé entre-temps
(`sold_chassis_active` : le rejeu renvoie alors `DUPLICATE` avec la vente concernée), rang
d'impression d'un reçu, téléphone d'un client créé en même temps (le rejeu le réutilise).
Une erreur détaillée du domaine (`ChassisAlreadySold`) n'est jamais rejouée.
"""

from collections.abc import Callable

from app.application.sales.ports import CUSTOMER_PHONE, RECEIPT_PRINT_SEQUENCE, SOLD_CHASSIS_ACTIVE
from app.application.stock.retry import MAX_ATTEMPTS, is_stock_race
from app.domain.sales.errors import ChassisAlreadySold
from app.domain.shared.errors import Duplicate, VersionConflict

RACES = frozenset({SOLD_CHASSIS_ACTIVE, RECEIPT_PRINT_SEQUENCE, CUSTOMER_PHONE})


def is_sale_race(error: Exception) -> bool:
    if isinstance(error, ChassisAlreadySold):
        return False
    if is_stock_race(error):
        return True
    return isinstance(error, Duplicate) and error.details.get("constraint") in RACES


def with_sale_retry[T](action: Callable[[], T], attempts: int = MAX_ATTEMPTS) -> T:
    if attempts < 1:
        msg = "with_sale_retry : au moins une tentative"
        raise ValueError(msg)
    for attempt in range(1, attempts + 1):
        try:
            return action()
        except (VersionConflict, Duplicate) as error:
            if not is_sale_race(error) or attempt == attempts:
                raise
    msg = "with_sale_retry : boucle terminée sans résultat"  # inatteignable (raise ci-dessus)
    raise AssertionError(msg)
