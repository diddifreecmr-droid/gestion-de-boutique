"""Ligne saisie → `SaleLine` vérifiée, instantanés et coûts figés (UC-VEN-01 étapes 2 à 4).

- Article lu **dans la transaction** de la vente, actif (un article archivé sort des listes de
  vente, UC-STK-04) ; nom et prix de base du jour copiés (instantanés), dernier coût et CMP
  copiés (coûts figés, RG-T13 : une correction d'achat ultérieure ne les touche pas).
- Mode de vente compatible avec l'unité de stock : « à l'unité » pour Unité et Pièce,
  « au mètre » pour Mètre, « à la pièce » pour un article au mètre vendu à la pièce
  (quantité de stock = pièces x longueur, dixième le plus proche, demi vers le haut, RG-X02).
  Prix de base de référence : celui de la pièce pour « à la pièce ».
- Détails vendus : seuls les champs de vente du profil sont admis (`sale_fields` : couleur,
  châssis, moteur pour les motos ; taille, couleur pour le prêt-à-porter).
"""

from decimal import ROUND_HALF_UP

from app.application.catalog.ports import ArticleRepository
from app.application.ports.uow import UnitOfWork
from app.application.sales.inputs import LineInput
from app.domain.catalog.article import Article
from app.domain.catalog.prices import PriceKind
from app.domain.profiles.profile import ShopProfile
from app.domain.sales.lines import SaleLine, SaleMode, SoldDetail
from app.domain.shared.errors import InvalidQuantity, ValidationFailed
from app.domain.shared.money import Money
from app.domain.shared.quantity import TENTH, Quantity, StockUnit

_MODES = {
    StockUnit.UNIT: frozenset({SaleMode.UNIT}),
    StockUnit.PIECE: frozenset({SaleMode.UNIT}),
    StockUnit.METER: frozenset({SaleMode.METER, SaleMode.PIECE}),
}


def _refused(field: str, message: str) -> ValidationFailed:
    return ValidationFailed(message, details={"field": field})


def default_mode(article: Article) -> SaleMode:
    unit = article.details.fields.stock_unit
    return SaleMode.METER if unit is StockUnit.METER else SaleMode.UNIT


def stock_quantity(article: Article, mode: SaleMode, quantity: Quantity) -> Quantity:
    fields = article.details.fields
    if mode not in _MODES[fields.stock_unit]:
        raise _refused("lines.sale_mode", "Mode de vente incompatible avec cet article")
    if mode is SaleMode.UNIT:
        return Quantity.of(quantity.value, fields.stock_unit)
    if mode is SaleMode.METER:
        return quantity
    if not fields.sold_by_piece or fields.piece_length_m is None:
        raise _refused("lines.sale_mode", "Cet article ne se vend pas à la pièce")
    meters = (quantity.value * fields.piece_length_m).quantize(TENTH, rounding=ROUND_HALF_UP)
    return Quantity.of(meters, StockUnit.METER).require_positive("lines.quantity")


def entered(item: LineInput, mode: SaleMode) -> Quantity:
    """Quantité saisie : au dixième au mètre (2,55 m refusé, ERR3-09), entière sinon."""
    grain = StockUnit.METER if mode is SaleMode.METER else StockUnit.UNIT
    try:
        quantity = Quantity.of(item.quantity, grain)
    except InvalidQuantity as exc:  # même erreur, avec le champ fautif pour le client
        raise InvalidQuantity(
            exc.message, details={**exc.details, "field": "lines.quantity"}
        ) from exc
    return quantity.require_positive("lines.quantity")


def check_details(details: tuple[SoldDetail, ...], profile: ShopProfile) -> None:
    allowed = {spec.code for spec in profile.sale_fields}
    for detail in details:
        unknown = sorted(set(detail.filled()) - allowed)
        if unknown:
            msg = "Détail inconnu pour ce type de boutique"
            raise ValidationFailed(msg, details={"field": "lines.details", "fields": unknown})


def resolve_line(
    uow: UnitOfWork, item: LineInput, profile: ShopProfile
) -> tuple[SaleLine, Article]:
    article = ArticleRepository.within(uow).get(item.article_id)
    if not article.is_active:
        raise _refused("lines.article_id", "Article archivé : il ne se vend plus")
    mode = item.sale_mode or default_mode(article)
    quantity = entered(item, mode)
    check_details(item.details, profile)
    kind = PriceKind.BASE_PIECE if mode is SaleMode.PIECE else PriceKind.BASE
    line = SaleLine(
        article_id=article.id,
        article_name=article.display_name,
        sale_mode=mode,
        quantity=quantity.value,
        stock_quantity=stock_quantity(article, mode, quantity),
        unit_price=Money.entry(item.unit_price, "lines.unit_price"),
        base_price=article.prices.of(kind),
        frozen_last_cost=article.last_cost,
        frozen_wac=article.wac,
        details=item.details,
    )
    return line, article


def minimum_of(article: Article, line: SaleLine, *, enabled: bool) -> Money | None:
    """Prix minimum appliqué à la ligne (H9) : `None` si le réglage est inactif."""
    kind = PriceKind.MINIMUM_PIECE if line.sale_mode is SaleMode.PIECE else PriceKind.MINIMUM
    return article.prices.active_minimum(kind, min_price_enabled=enabled)
