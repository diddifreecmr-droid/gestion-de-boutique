"""Modèle d'import **Articles** (T33, CDC § 15.1 ; SCN-L3-04 étape 1).

Colonnes du profil (`article_columns`) ; propriétaire et comptable (`IMPORT_ARTICLES`), le
comptable sans prix (voir `article_rows.py`). Doublons signalés et ignorés ; aperçu :
« 2 articles nouveaux seront créés ». Écriture : un article par ligne acceptée, tracé dans le
lot (`ImportedEntity.ARTICLE`).
"""

from collections.abc import Sequence

from app.application.catalog.use_cases.context import shop_context
from app.application.imports.kinds.article_rows import (
    ArticlePlanner,
    PlannedArticle,
    create_article,
)
from app.application.imports.models import ImportModel, ImportRun, ModelCheck
from app.application.imports.verdicts import RowRefused, Verdict, created_note
from app.application.ports.uow import UnitOfWork
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.domain.imports.article_columns import article_columns
from app.domain.imports.batch import ImportedItem
from app.domain.imports.sheet import ParsedRow
from app.domain.imports.template import TemplateSpec
from app.domain.imports.values import ImportedEntity, ImportKind
from app.domain.profiles.profile import ShopProfile

INSTRUCTIONS = (
    "Un article par ligne ; un article déjà présent dans la boutique (même nom, même marque et"
    " modèle ou même référence) est signalé en doublon et ignoré.",
    "Les prix sont facultatifs et réservés au propriétaire.",
    "Ordre conseillé : Articles, puis Stock de départ.",
)


def articles_note(count: int) -> str | None:
    return created_note(count, "article nouveau sera créé", "articles nouveaux seront créés")


class ArticlesImport(ImportModel):
    kind = ImportKind.ARTICLES
    permission = Permission.IMPORT_ARTICLES

    def template(self, profile: ShopProfile) -> TemplateSpec:
        return TemplateSpec(
            kind=self.kind, columns=article_columns(profile), instructions=INSTRUCTIONS
        )

    def _plan(
        self, uow: UnitOfWork, actor: Actor, rows: Sequence[ParsedRow]
    ) -> tuple[Verdict, list[PlannedArticle]]:
        profile = shop_context(uow).profile
        planner = ArticlePlanner(uow, actor, article_columns(profile))
        verdict, planned = Verdict(), []
        for row in rows:
            try:
                planned.append(planner.plan(row))
            except RowRefused as refused:
                verdict.refuse(row.line, refused.column, refused.message)
            else:
                verdict.accept(row.line)
        return verdict, planned

    def check(self, uow: UnitOfWork, actor: Actor, rows: Sequence[ParsedRow]) -> ModelCheck:
        verdict, planned = self._plan(uow, actor, rows)
        return verdict.check(articles_note(len(planned)))

    def apply(
        self, uow: UnitOfWork, actor: Actor, rows: Sequence[ParsedRow], run: ImportRun
    ) -> tuple[ImportedItem, ...]:
        verdict, planned = self._plan(uow, actor, rows)
        verdict.require_all_accepted(rows)
        context = shop_context(uow)
        return tuple(
            ImportedItem(item.line, ImportedEntity.ARTICLE, create_article(
                uow, actor, item, run, context
            ).id.value)
            for item in planned
        )  # fmt: skip
