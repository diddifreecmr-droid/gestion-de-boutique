"""Lignes du Stock de départ : article, lieu, quantité, coût unitaire, date (CDC § 15.1).

Contrôle d'une ligne (lecture seule) :

- **lieu** : nom d'un lieu actif de la boutique (sans casse) ; inconnu ou désactivé → erreur ;
- **article** : Motos, marque + modèle ; autres profils, référence puis nom (sans casse ni
  accent). Archivé → erreur. **Inconnu** : proposé à la création (UC-IMP-02 étape 3,
  SCN-L3-04 étape 2) si le profil le permet avec ce seul nom (Prêt-à-porter, Motos) ; sinon
  (Textile : unité obligatoire) erreur « importez-le d'abord avec le modèle Articles ». Un même
  article nouveau cité sur plusieurs lignes n'est créé qu'une fois ;
- **quantité** > 0 dans l'unité de stock de l'article (au dixième pour le mètre) ;
  **coût unitaire** FCFA ≥ 0 ; **date** jamais future, recul limité hors propriétaire (RG-T09) ;
- **doublon** (même article + même lieu) : déjà plus haut dans le fichier, ou stock de départ
  déjà importé (mouvement « Reprise de départ » non annulé) → signalé et ignoré.
"""

from dataclasses import dataclass, field
from datetime import date

from app.application.catalog.ports import (
    ARTICLE_BRAND_MODEL,
    ARTICLE_NAME,
    ARTICLE_REFERENCE,
    ArticleRepository,
)
from app.application.catalog.use_cases.context import shop_context
from app.application.imports.kinds.article_rows import PlannedArticle, read_details
from app.application.imports.verdicts import (
    RowRefused,
    amount,
    day,
    number,
    problem_of,
    required_text,
)
from app.application.ports.uow import UnitOfWork
from app.application.security.actor import Actor
from app.application.shops.ports import LocationRepository
from app.application.stock.ports import StockMovementLog
from app.domain.catalog.article import Article
from app.domain.catalog.ids import ArticleId
from app.domain.catalog.keys import identity_key
from app.domain.imports.sheet import ParsedRow
from app.domain.shared.business_day import validate_entry_date
from app.domain.shared.errors import DomainError
from app.domain.shared.money import Money
from app.domain.shared.quantity import Quantity, StockUnit
from app.domain.shared.roles import Role
from app.domain.shops.location import Location
from app.domain.shops.values import name_key
from app.domain.stock.values import MovementType

QUANTITY, DAY, PLACE = "Quantité", "Date du stock", "Lieu"
CREATE_FIRST = "article « {} » inconnu : importez-le d'abord avec le modèle Articles ({})"


@dataclass(frozen=True, slots=True)
class OpeningLine:
    line: int
    article: Article | PlannedArticle
    location: Location
    quantity: Quantity
    unit_cost: Money
    stock_day: date | None


@dataclass
class OpeningPlanner:
    uow: UnitOfWork
    actor: Actor
    today: date
    seen: dict[tuple[str, str], int] = field(default_factory=dict)
    new_articles: dict[str, PlannedArticle] = field(default_factory=dict)
    _opened: dict[ArticleId, set[str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.profile = shop_context(self.uow).profile
        self.by_model = any(spec.code == "model" for spec in self.profile.article_fields)
        self.articles = ArticleRepository.within(self.uow)
        places = LocationRepository.within(self.uow).list_all()
        self.places = {place.name_key: place for place in places}

    # ------------------------------------------------------------------ lieu, article
    def _location(self, wanted: str) -> Location:
        place = self.places.get(name_key(wanted))
        if place is None:
            raise RowRefused(PLACE, f"le lieu « {wanted} » est inconnu")
        if not place.active:
            raise RowRefused(PLACE, f"le lieu « {wanted} » est désactivé")
        return place

    def _lookup(self, values: dict[str, str]) -> tuple[str, Article | None]:
        if self.by_model:
            key = identity_key(values["brand"], values["model"])
            return key, self.articles.find_by_key(ARTICLE_BRAND_MODEL, key)
        key = identity_key(values["name"])
        found = self.articles.find_by_key(ARTICLE_REFERENCE, key)
        return key, found or self.articles.find_by_key(ARTICLE_NAME, key)

    def _article(self, line: int, values: dict[str, str]) -> tuple[str, Article | PlannedArticle]:
        """Clé du doublon (identifiant ou clé de l'article nouveau) et article."""
        key, found = self._lookup(values)
        if found is not None:
            if not found.is_active:
                raise RowRefused(None, f"l'article « {found.display_name} » est archivé")
            return str(found.id), found
        if key in self.new_articles:
            return key, self.new_articles[key]
        try:
            details = read_details(self.profile, values)
        except RowRefused as refused:
            message = CREATE_FIRST.format(self._wanted(values), refused.message)
            raise RowRefused(None, message) from None
        return key, PlannedArticle(line, details, None)

    def _already_opened(self, article: Article | PlannedArticle, place: Location) -> bool:
        if not isinstance(article, Article):
            return False
        if article.id not in self._opened:
            movements = StockMovementLog.within(self.uow).chronology(article.id)
            reversed_ids = {m.reverses for m in movements if m.reverses is not None}
            self._opened[article.id] = {
                str(m.location_id)
                for m in movements
                if m.type is MovementType.OPENING and m.id not in reversed_ids
            }
        return str(place.id) in self._opened[article.id]

    # ------------------------------------------------------------------ ligne
    def _wanted(self, values: dict[str, str]) -> str:
        return " ".join(values.values())

    def plan(self, row: ParsedRow) -> OpeningLine:
        codes = ("brand", "model") if self.by_model else ("name",)
        values = {code: required_text(row, code) for code in codes}
        place = self._location(required_text(row, "location"))
        article_key, article = self._article(row.line, values)
        unit = article.details.fields.stock_unit
        quantity = self._quantity(row, unit)
        cost = amount(row, "unit_cost")
        if cost is None:
            msg = "Coût unitaire obligatoire vide après nettoyage"
            raise RuntimeError(msg)
        stock_day = self._day(day(row, "stock_day"))
        duplicate_key = (article_key, str(place.id))
        if duplicate_key in self.seen:
            message = f"doublon : « {self._wanted(values)} » à {place.name} figure déjà ligne"
            raise RowRefused(None, f"{message} {self.seen[duplicate_key]}")
        if self._already_opened(article, place):
            message = (
                f"doublon : stock de départ déjà importé pour « {article.details.display_name}"
            )
            raise RowRefused(None, f"{message} » à {place.name}")
        self.seen[duplicate_key] = row.line
        if isinstance(article, PlannedArticle):
            self.new_articles.setdefault(article_key, article)
        return OpeningLine(row.line, article, place, quantity, Money(cost), stock_day)

    def _quantity(self, row: ParsedRow, unit: StockUnit) -> Quantity:
        value = number(row, "quantity")
        if value is None:
            msg = "Quantité obligatoire vide après nettoyage"
            raise RuntimeError(msg)
        try:
            return Quantity.of(value, unit).require_positive("quantity")
        except DomainError as error:
            raise RowRefused(QUANTITY, f"la quantité : {problem_of(error)}") from error

    def _day(self, wanted: date | None) -> date | None:
        if wanted is None:
            return None
        try:
            owner = self.actor.role is Role.OWNER
            return validate_entry_date(wanted, self.today, is_owner=owner)
        except DomainError as error:
            raise RowRefused(DAY, f"la date du stock : {problem_of(error)}") from error
