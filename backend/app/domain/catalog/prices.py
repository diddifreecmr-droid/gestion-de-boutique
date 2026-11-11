"""Prix de vente d'un article et historique des prix (UC-STK-03, CDC § 20.2, H9).

- Quatre prix, tous facultatifs (FCFA entiers, jamais négatifs, RG-T07) : prix de base (au mètre
  pour le textile), prix de base à la pièce, prix minimum et minimum à la pièce. Un prix de 0
  est admis (Q-34 ouverte : « cadeau »), il reste distinct de « pas de prix » (`None`).
- Q-34 retenue : un prix minimum **supérieur** au prix de base est refusé
  (`MIN_PRICE_ABOVE_BASE`).
- Les prix à la pièce n'ont de sens que pour un article vendu à la pièce
  (`PIECE_PRICE_NOT_ALLOWED`, vérifié par l'article).
- Le prix minimum n'est **actif** que si le réglage de la boutique l'active
  (`active_minimum`) ; un minimum stocké reste inerte si le réglage est désactivé ensuite.
- `PriceHistory` : une ligne par prix changé (date d'effet, ancien, nouveau, auteur). Un
  nouveau prix vaut pour les ventes suivantes ; les ventes passées gardent leur instantané.
"""

from dataclasses import dataclass, fields
from datetime import datetime
from enum import StrEnum

from app.domain.audit.values import Scalar
from app.domain.catalog.errors import MinPriceAboveBase, MinPriceDisabled, PiecePriceNotAllowed
from app.domain.catalog.ids import ArticleId, PriceHistoryId
from app.domain.shared.business_day import require_aware
from app.domain.shared.ids import ShopId, UserId
from app.domain.shared.money import Money


class PriceKind(StrEnum):
    """« Prix concerné » de l'historique (CDC § 20.2) ; valeur = nom du champ de prix."""

    BASE = "base_price"
    BASE_PIECE = "base_price_piece"
    MINIMUM = "min_price"
    MINIMUM_PIECE = "min_price_piece"


PIECE_KINDS = frozenset({PriceKind.BASE_PIECE, PriceKind.MINIMUM_PIECE})
MINIMUM_KINDS = frozenset({PriceKind.MINIMUM, PriceKind.MINIMUM_PIECE})


def _entry(value: object, field: str) -> Money | None:
    if value is None:
        return None
    if not isinstance(value, Money):
        msg = f"ArticlePrices.{field} doit être un Money ou None"
        raise TypeError(msg)
    return value.require_non_negative(field)


@dataclass(frozen=True, slots=True, kw_only=True)
class ArticlePrices:
    base_price: Money | None = None
    base_price_piece: Money | None = None
    min_price: Money | None = None
    min_price_piece: Money | None = None

    def __post_init__(self) -> None:
        for kind in PriceKind:
            _entry(getattr(self, kind.value), kind.value)
        pairs = (
            (self.min_price, self.base_price, PriceKind.MINIMUM),
            (self.min_price_piece, self.base_price_piece, PriceKind.MINIMUM_PIECE),
        )
        for minimum, base, kind in pairs:
            if minimum is not None and base is not None and minimum > base:
                raise MinPriceAboveBase(kind.value, minimum.amount, base.amount)

    def of(self, kind: PriceKind) -> Money | None:
        price: Money | None = getattr(self, kind.value)
        return price

    def set_kinds(self) -> frozenset[PriceKind]:
        """Prix renseignés (non `None`)."""
        return frozenset(kind for kind in PriceKind if self.of(kind) is not None)

    def active_minimum(self, kind: PriceKind, *, min_price_enabled: bool) -> Money | None:
        """Prix minimum appliqué à la vente : `None` si le réglage est désactivé (H9)."""
        if kind not in MINIMUM_KINDS:
            msg = f"{kind} n'est pas un prix minimum"
            raise ValueError(msg)
        return self.of(kind) if min_price_enabled else None

    def scalars(self) -> dict[str, Scalar]:
        return {
            item.name: None if (price := getattr(self, item.name)) is None else price.amount
            for item in fields(self)
        }


@dataclass(frozen=True, slots=True)
class PriceChange:
    kind: PriceKind
    old: Money | None
    new: Money | None


def price_changes(
    current: ArticlePrices,
    new: ArticlePrices,
    *,
    sold_by_piece: bool,
    min_price_enabled: bool,
) -> list[PriceChange]:
    """Prix changés de `current` à `new`, après contrôle des règles de saisie (UC-STK-03).

    Un prix à la pièce exige un article vendu à la pièce ; un minimum **nouveau ou modifié**
    exige le réglage « prix minimum » (un minimum déjà stocké peut être gardé ou retiré).
    """
    changed = [
        PriceChange(kind, current.of(kind), new.of(kind))
        for kind in PriceKind
        if current.of(kind) != new.of(kind)
    ]
    for change in changed:
        if change.new is None:
            continue
        if change.kind in PIECE_KINDS and not sold_by_piece:
            raise PiecePriceNotAllowed(change.kind.value)
        if change.kind in MINIMUM_KINDS and not min_price_enabled:
            raise MinPriceDisabled(change.kind.value)
    return changed


@dataclass(frozen=True, slots=True, kw_only=True)
class PriceHistory:
    """Ligne d'historique, immuable (ajout seul : jamais modifiée ni supprimée)."""

    id: PriceHistoryId
    shop_id: ShopId
    article_id: ArticleId
    kind: PriceKind
    old_price: Money | None
    new_price: Money | None
    effective_at: datetime
    author_id: UserId

    def __post_init__(self) -> None:
        if not isinstance(self.article_id, ArticleId) or not isinstance(self.author_id, UserId):
            msg = "PriceHistory exige un ArticleId et un UserId"
            raise TypeError(msg)
        object.__setattr__(self, "kind", PriceKind(self.kind))
        object.__setattr__(self, "effective_at", require_aware(self.effective_at))

    @classmethod
    def record(
        cls,
        shop_id: ShopId,
        article_id: ArticleId,
        change: PriceChange,
        *,
        author_id: UserId,
        at: datetime,
    ) -> "PriceHistory":
        return cls(
            id=PriceHistoryId.new(),
            shop_id=shop_id,
            article_id=article_id,
            kind=change.kind,
            old_price=change.old,
            new_price=change.new,
            effective_at=at,
            author_id=author_id,
        )
