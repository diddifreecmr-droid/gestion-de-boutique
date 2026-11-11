"""Avertissement « prix très différent du dernier coût » (UC-ACH-01, recette PUR-02).

Une ligne est signalée si son prix **par unité de stock** (total de ligne / quantité de stock,
hors frais) s'écarte de plus de 30 % du dernier coût de l'article : `|prix - coût| x 10 >
3 x coût`, en fractions exactes. Dernier coût 520 000 : 364 000 (-30 % exact) passe, 363 999
et 52 000 sont signalés. Sans dernier coût connu (ou à 0), rien n'est comparé.

L'achat est alors refusé (`PriceGapToConfirm`, 422) tant que l'utilisateur n'a pas confirmé
(`confirm_price_gap: true`). Correction : seules les lignes nouvelles ou modifiées sont
comparées, au dernier coût **hors cet achat** (le prix erroné ne sert pas de référence,
SCN-04 : 350 000 corrigé en 530 000 se compare à 500 000).
"""

from collections.abc import Callable, Iterable
from fractions import Fraction

from app.domain.catalog.ids import ArticleId
from app.domain.purchasing.errors import PriceGapToConfirm
from app.domain.purchasing.lines import CostedLine
from app.domain.shared.money import Money

GAP_NUMERATOR, GAP_DENOMINATOR = 3, 10  # 30 %


def is_far(price: Fraction, reference: Money) -> bool:
    if reference.amount == 0:
        return False
    return abs(price - reference.amount) * GAP_DENOMINATOR > GAP_NUMERATOR * reference.amount


def require_confirmed(
    lines: Iterable[tuple[int, CostedLine]],
    reference: Callable[[ArticleId], Money | None],
    *,
    confirmed: bool,
) -> None:
    """Lève `PriceGapToConfirm` (toutes les lignes en cause) si une ligne s'écarte trop."""
    if confirmed:
        return
    gaps = []
    for index, line in lines:
        last = reference(line.line.article_id)
        price = Fraction(line.total.amount) / Fraction(line.stock_quantity.value)
        if last is not None and is_far(price, last):
            gaps.append(
                {
                    "line": index,
                    "article_id": str(line.line.article_id),
                    "last_cost": last.amount,
                    "unit_price": line.line.unit_price.amount,
                }
            )
    if gaps:
        raise PriceGapToConfirm(gaps)
