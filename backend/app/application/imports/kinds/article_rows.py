"""Lignes d'articles à créer : lecture, contrôle et écriture (modèles Articles et Stock de départ).

Contrôle d'une ligne, sans rien écrire (UC-STK-01 appliqué ligne par ligne) :

1. champs du profil lus dans leur type (`field_value`) puis validés par le domaine
   (`build_details` : Motos, marque + modèle ; Textile, unité…) ;
2. prix : **le propriétaire seul** les fixe (`PRICE_SET`, comme `CreateArticle`) — un comptable
   qui en remplit reçoit une erreur de ligne, jamais un prix posé en silence ; minimum au-dessus
   du prix de vente refusé ;
3. doublon (même marque + modèle, même nom, même référence, sans casse ni accent) : déjà dans la
   boutique, ou déjà plus haut dans le fichier → ligne signalée et ignorée.

Écriture (`create_article`) : référence générée si vide (`REF-000001`), prix et historique des
prix, événement « Créer » au journal — exactement comme une création à l'écran.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal

from app.application.catalog.ports import ArticleRepository
from app.application.catalog.use_cases.context import (
    ArticleInput,
    ShopCatalogContext,
    build_details,
    ensure_reference,
    record_history,
    require_unique,
    shop_context,
)
from app.application.imports.models import ImportRun
from app.application.imports.verdicts import RowRefused, amount, number, problem_of
from app.application.ports.uow import UnitOfWork
from app.application.security.access import Access
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.role_matrix import access_for
from app.domain.catalog.article import Article
from app.domain.catalog.details import ArticleDetails
from app.domain.catalog.errors import DuplicateArticle
from app.domain.catalog.prices import ArticlePrices, PriceKind
from app.domain.imports.article_columns import field_value
from app.domain.imports.columns import ColumnSpec
from app.domain.imports.problems import CellRejected
from app.domain.imports.sheet import ParsedRow
from app.domain.profiles.profile import ShopProfile
from app.domain.shared.errors import DomainError
from app.domain.shared.money import Money

PRICE_RESERVED = "les prix sont fixés par le propriétaire : laissez les colonnes de prix vides"


@dataclass(frozen=True, slots=True)
class PlannedArticle:
    line: int
    details: ArticleDetails
    prices: ArticlePrices | None


def may(actor: Actor, permission: Permission) -> bool:
    return actor.role is not None and access_for(actor.role, permission) is not Access.NONE


def _prices(actor: Actor, row: ParsedRow, headers: Mapping[str, str]) -> ArticlePrices | None:
    found = {kind: amount(row, kind.value) for kind in PriceKind if kind.value in headers}
    given = {kind: value for kind, value in found.items() if value is not None}
    if not given:
        return None
    if not may(actor, Permission.PRICE_SET):
        raise RowRefused(headers[next(iter(given)).value], PRICE_RESERVED)
    try:
        return ArticlePrices(**{kind.value: Money(value) for kind, value in given.items()})
    except DomainError as error:
        raise RowRefused(headers[PriceKind.MINIMUM.value], problem_of(error)) from error


def read_details(
    profile: ShopProfile, values: Mapping[str, object], threshold: Decimal | None = None
) -> ArticleDetails:
    """Détails validés par le domaine ; `RowRefused` (sans colonne) sinon."""
    try:
        data = ArticleInput(
            fields={code: value for code, value in values.items() if value is not None},
            alert_threshold=threshold,
        )
        return build_details(profile, data)
    except DomainError as error:
        raise RowRefused(None, problem_of(error)) from error


@dataclass
class ArticlePlanner:
    """Contrôle des lignes d'un même fichier (doublons entre lignes compris)."""

    uow: UnitOfWork
    actor: Actor
    columns: tuple[ColumnSpec, ...]
    seen: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.profile = shop_context(self.uow).profile
        self.articles = ArticleRepository.within(self.uow)
        self.headers = {column.key: column.header for column in self.columns}

    def plan(self, row: ParsedRow) -> PlannedArticle:
        values: dict[str, object] = {}
        for spec in self.profile.article_fields:
            try:
                values[spec.code] = field_value(spec, row.values.get(spec.code))
            except CellRejected as rejected:
                column = next(c for c in self.columns if c.key == spec.code)
                raise RowRefused(column.header, f"{column.subject} : {rejected.message}") from None
        details = read_details(self.profile, values, number(row, "alert_threshold"))
        prices = _prices(self.actor, row, self.headers)
        self.require_new(details, row.line)
        return PlannedArticle(row.line, details, prices)

    def require_new(self, details: ArticleDetails, line: int) -> None:
        try:
            require_unique(self.articles, details)
        except DuplicateArticle as duplicate:
            name = duplicate.details["existing_name"]
            message = f"doublon : l'article « {name} » existe déjà"
            raise RowRefused(None, message) from duplicate
        keys = [details.brand_model_key, details.name_key, details.reference_key]
        for key in (k for k in keys if k is not None):
            if key in self.seen:
                message = f"doublon : « {details.display_name} » figure déjà ligne {self.seen[key]}"
                raise RowRefused(None, message)
        for key in (k for k in keys if k is not None):
            self.seen[key] = line


def create_article(
    uow: UnitOfWork,
    actor: Actor,
    planned: PlannedArticle,
    run: ImportRun,
    context: ShopCatalogContext,
) -> Article:
    details = ensure_reference(uow, context.profile, planned.details)
    article = Article.create(uow.shop_id, details, performer=run.performer, now=run.now)
    if planned.prices is not None:
        changes = article.set_prices(
            planned.prices,
            min_price_enabled=context.settings.min_price_enabled,
            performer=run.performer,
            now=run.now,
        )
        record_history(uow, article, changes, author_id=actor.user_id, at=run.now)
    ArticleRepository.within(uow).add(article)
    return article
