"""`GET /imports/templates/{kind}` — modèle `.xlsx` à remplir (UC-IMP-01, IMP-01, IMP-02).

Colonnes selon le profil de la boutique, listes déroulantes remplies avec ses données (lieux,
catégories, types de client), feuille « Mode d'emploi ». Lecture seule : rien n'est écrit.
"""

from dataclasses import dataclass

from app.application.imports.access import ImportAccess, shop_profile
from app.application.imports.choices import choice_list
from app.application.imports.ports import SpreadsheetWriter
from app.application.imports.workbook import TemplateWorkbook
from app.application.ports.uow import UnitOfWorkFactory
from app.application.security.actor import Actor
from app.application.shops.context import actor_shop
from app.domain.imports.values import ImportKind, SpreadsheetFormat


@dataclass(frozen=True, slots=True)
class TemplateFile:
    kind: ImportKind
    content: bytes

    @property
    def file_name(self) -> str:
        return f"modele-import-{self.kind.value.replace('_', '-')}.xlsx"

    @property
    def media_type(self) -> str:
        return SpreadsheetFormat.XLSX.value


class DownloadImportTemplate:
    def __init__(
        self, uow_factory: UnitOfWorkFactory, access: ImportAccess, writer: SpreadsheetWriter
    ) -> None:
        self._uow_factory = uow_factory
        self._access = access
        self._writer = writer

    def execute(self, actor: Actor, kind: str) -> TemplateFile:
        with self._uow_factory(actor_shop(actor)) as uow:
            model = self._access.require(uow, actor, kind)
            spec = model.template(shop_profile(uow))
            if spec.kind is not model.kind:
                msg = f"Le modèle {model.kind} décrit un autre modèle ({spec.kind})"
                raise RuntimeError(msg)
            sources = {c.choices for c in spec.columns if c.choices is not None}
            lists = {source: choice_list(uow, source) for source in sources}
        workbook = TemplateWorkbook(spec=spec, lists=lists)
        return TemplateFile(model.kind, self._writer.template(workbook))
