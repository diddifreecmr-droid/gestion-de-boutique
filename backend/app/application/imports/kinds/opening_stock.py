"""Modèle d'import **Stock de départ** (T33, CDC § 15.1 ; SCN-L3-04 étapes 2 et 3).

Colonnes : article (Motos : Marque *, Modèle * ; sinon Article * — nom ou référence), Lieu *,
Quantité *, Coût unitaire *, Date du stock. Propriétaire et comptable (`IMPORT_STOCK`).

Écriture, par ligne acceptée (voir `opening_rows.py` pour le contrôle) :

1. article inconnu proposé à la création : créé une fois (`ImportedEntity.ARTICLE`) ;
2. mouvement **« Reprise de départ »** (`MovementType.OPENING`) au lieu, coût unitaire saisi,
   document lié = le lot (`SourceType.IMPORT`, `IMP-…`), par le grand livre (`StockLedger`) ;
3. coûts de l'article rejoués d'après le grand livre (`refresh_costs`) : pour un article sans
   autre entrée, le coût unitaire devient **le premier CMP et le dernier coût**.
"""

from collections.abc import Sequence

from app.application.catalog.use_cases.context import shop_context
from app.application.imports.kinds.article_rows import PlannedArticle, create_article
from app.application.imports.kinds.articles import articles_note
from app.application.imports.kinds.opening_rows import OpeningLine, OpeningPlanner
from app.application.imports.models import ImportModel, ImportRun, ModelCheck
from app.application.imports.verdicts import RowRefused, Verdict, created_note
from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWork
from app.application.purchasing.costs import refresh_costs
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.stock.ledger import StockLedger
from app.application.stock.postings import Posting
from app.domain.catalog.article import Article
from app.domain.catalog.ids import ArticleId
from app.domain.imports.batch import ImportedItem
from app.domain.imports.columns import ChoiceSource, ColumnKind, ColumnSpec
from app.domain.imports.sheet import ParsedRow
from app.domain.imports.template import TemplateSpec
from app.domain.imports.values import ImportedEntity, ImportKind
from app.domain.profiles.profile import ShopProfile
from app.domain.purchasing.values import entry_instant
from app.domain.stock.values import MovementType, SourceRef, SourceType

_ARTICLE = ColumnSpec(
    key="name", header="Article", subject="l'article", required=True, example="Chemise lin",
    help="Nom ou référence d'un article ; inconnu, il est proposé à la création.",
)  # fmt: skip
_BRAND = ColumnSpec(key="brand", header="Marque", subject="la marque", required=True,
                    example="Haojue")  # fmt: skip
_MODEL = ColumnSpec(key="model", header="Modèle", subject="le modèle", required=True,
                    example="HJ125-8")  # fmt: skip
_COMMON = (
    ColumnSpec(key="location", header="Lieu", subject="le lieu", required=True,
               choices=ChoiceSource.LOCATIONS, help="Un lieu de la boutique (liste).",
               example="Boutique"),
    ColumnSpec(key="quantity", header="Quantité", subject="la quantité", required=True,
               kind=ColumnKind.NUMBER, example="10",
               help="Dans l'unité de stock de l'article (au dixième pour le mètre)."),
    ColumnSpec(key="unit_cost", header="Coût unitaire", subject="le coût unitaire",
               required=True, kind=ColumnKind.AMOUNT, example="9 000",
               help="Coût d'achat d'une unité (FCFA) : il devient le premier CMP."),
    ColumnSpec(key="stock_day", header="Date du stock", subject="la date du stock",
               kind=ColumnKind.DATE, example="31/10/2026",
               help="Facultative : aujourd'hui si vide ; jamais dans le futur."),
)  # fmt: skip
INSTRUCTIONS = (
    "Une ligne par article et par lieu ; un article déjà repris à ce lieu est ignoré.",
    "Importez d'abord vos articles (modèle Articles) ; un article inconnu est proposé à la"
    " création quand son nom suffit.",
)


def entries_note(count: int) -> str | None:
    return created_note(
        count,
        "entrée « Reprise de départ » sera enregistrée",
        "entrées « Reprise de départ » seront enregistrées",
    )


class OpeningStockImport(ImportModel):
    kind = ImportKind.OPENING_STOCK
    permission = Permission.IMPORT_STOCK

    def __init__(self, clock: Clock) -> None:
        self._clock = clock
        self._ledger = StockLedger(clock)

    def template(self, profile: ShopProfile) -> TemplateSpec:
        by_model = any(spec.code == "model" for spec in profile.article_fields)
        first = (_BRAND, _MODEL) if by_model else (_ARTICLE,)
        return TemplateSpec(kind=self.kind, columns=(*first, *_COMMON), instructions=INSTRUCTIONS)

    def _plan(
        self, uow: UnitOfWork, actor: Actor, rows: Sequence[ParsedRow]
    ) -> tuple[Verdict, list[OpeningLine], int]:
        planner = OpeningPlanner(uow, actor, self._clock.today())
        verdict, lines = Verdict(), []
        for row in rows:
            try:
                lines.append(planner.plan(row))
            except RowRefused as refused:
                verdict.refuse(row.line, refused.column, refused.message)
            else:
                verdict.accept(row.line)
        return verdict, lines, len(planner.new_articles)

    def check(self, uow: UnitOfWork, actor: Actor, rows: Sequence[ParsedRow]) -> ModelCheck:
        verdict, lines, created = self._plan(uow, actor, rows)
        return verdict.check(articles_note(created), entries_note(len(lines)))

    def apply(
        self, uow: UnitOfWork, actor: Actor, rows: Sequence[ParsedRow], run: ImportRun
    ) -> tuple[ImportedItem, ...]:
        verdict, lines, _ = self._plan(uow, actor, rows)
        verdict.require_all_accepted(rows)
        context = shop_context(uow)
        source = SourceRef(SourceType.IMPORT, run.batch_id.value, str(run.number))
        created: dict[int, Article] = {}
        items: list[ImportedItem] = []
        touched: list[ArticleId] = []
        for line in lines:
            article = line.article
            if isinstance(article, PlannedArticle):
                if id(article) not in created:
                    created[id(article)] = create_article(uow, actor, article, run, context)
                    new_id = created[id(article)].id.value
                    items.append(ImportedItem(article.line, ImportedEntity.ARTICLE, new_id))
                article = created[id(article)]
            day = line.stock_day
            posting = Posting(
                article_id=article.id,
                location_id=line.location.id,
                type=MovementType.OPENING,
                quantity=line.quantity,
                source=source,
                occurred_at=run.now if day is None else entry_instant(day, run.now),
                author_id=actor.user_id,
                unit_cost=line.unit_cost,
            )
            movement = self._ledger.record_entry(uow, posting)
            items.append(ImportedItem(line.line, ImportedEntity.STOCK_MOVEMENT, movement.id.value))
            touched.append(article.id)
        refresh_costs(uow, touched)
        return tuple(items)
