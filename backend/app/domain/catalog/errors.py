"""Erreurs métier du catalogue (codes ajoutés par T13, recette Q-31/Q-34) → HTTP 422 sauf mention.

| Erreur | Code | Cas |
| --- | --- | --- |
| `DuplicateArticle` | `DUPLICATE` (409) | même marque + modèle ou référence (UC-STK-01) |
| `ArticleHasStock` | `ARTICLE_HAS_STOCK` | archiver un article qui a du stock (CAT-12) |
| `MinPriceAboveBase` | `MIN_PRICE_ABOVE_BASE` | Q-34 : minimum supérieur au prix de base |
| `MinPriceDisabled` | `MIN_PRICE_DISABLED` | minimum saisi, réglage « prix minimum » inactif |
| `PiecePriceNotAllowed` | `PIECE_PRICE_NOT_ALLOWED` | prix à la pièce sans vente à la pièce |

`DuplicateArticle.details.existing_id` désigne l'article existant (l'écran le propose).
"""

from app.domain.shared.errors import DomainError, Duplicate


class DuplicateArticle(Duplicate):
    """L'article existe déjà : l'erreur le désigne pour que l'écran le propose (UC-STK-01)."""

    def __init__(self, existing_id: str, existing_name: str, constraint: str) -> None:
        super().__init__(
            "Cet article existe déjà",
            details={
                "existing_id": existing_id,
                "existing_name": existing_name,
                "constraint": constraint,
            },
        )


class ArticleHasStock(DomainError):
    code = "ARTICLE_HAS_STOCK"

    def __init__(self, article_id: str) -> None:
        super().__init__(
            "Cet article a encore du stock : il ne peut pas être archivé",
            details={"article_id": article_id},
        )


class MinPriceAboveBase(DomainError):
    code = "MIN_PRICE_ABOVE_BASE"

    def __init__(self, field: str, minimum: int, base: int) -> None:
        super().__init__(
            "Le prix minimum ne peut pas dépasser le prix de base",
            details={"field": field, "min_price": minimum, "base_price": base},
        )


class MinPriceDisabled(DomainError):
    code = "MIN_PRICE_DISABLED"

    def __init__(self, field: str) -> None:
        super().__init__(
            "Le prix minimum est désactivé dans les réglages de la boutique",
            details={"field": field},
        )


class PiecePriceNotAllowed(DomainError):
    code = "PIECE_PRICE_NOT_ALLOWED"

    def __init__(self, field: str) -> None:
        super().__init__(
            "Prix à la pièce réservé à un article vendu à la pièce", details={"field": field}
        )
