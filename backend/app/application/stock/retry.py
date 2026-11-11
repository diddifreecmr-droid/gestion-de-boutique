"""Réessai borné d'une transaction de stock sur conflit de concurrence (specs § 10, ERR-STK-05).

Deux sorties simultanées de la même projection : la seconde à valider échoue
(`VersionConflict`, ou `Duplicate` sur `stock_level_article_location` si la projection naissait
dans les deux). La transaction **entière** est rejouée (lecture fraîche du stock) au plus
`MAX_ATTEMPTS` fois : la seconde vente voit alors le stock à jour et reçoit, le cas échéant,
`STOCK_INSUFFICIENT`. Au-delà, l'erreur de concurrence remonte (409), jamais avalée.

`action` doit ouvrir **sa propre** unité de travail à chaque appel (aucun état partagé).
"""

from collections.abc import Callable

from app.application.stock.ports import STOCK_LEVEL_KEY
from app.domain.shared.errors import Duplicate, VersionConflict

MAX_ATTEMPTS = 3


def is_stock_race(error: Exception) -> bool:
    if isinstance(error, VersionConflict):
        return True
    return isinstance(error, Duplicate) and error.details.get("constraint") == STOCK_LEVEL_KEY


def with_stock_retry[T](action: Callable[[], T], attempts: int = MAX_ATTEMPTS) -> T:
    if attempts < 1:
        msg = "with_stock_retry : au moins une tentative"
        raise ValueError(msg)
    for attempt in range(1, attempts + 1):
        try:
            return action()
        except (VersionConflict, Duplicate) as error:
            if not is_stock_race(error) or attempt == attempts:
                raise
    msg = "with_stock_retry : boucle terminée sans résultat"  # inatteignable (raise ci-dessus)
    raise AssertionError(msg)
