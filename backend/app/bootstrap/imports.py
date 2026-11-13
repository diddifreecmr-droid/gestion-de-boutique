"""Assemblage de l'import (TR-22) : tableurs `openpyxl`/CSV, stockage partagé, modèles.

- Le fichier d'aperçu va dans le **même** `FileStorage` que les pièces jointes (Silo en prod).
- `MODELS` : registre des modèles branchés. Vide au socle (T32) ; les 5 modèles s'y ajoutent
  une ligne chacun : Articles et Stock de départ (T33), Clients, Créances en cours et
  Fournisseurs (T34). Un modèle absent répond 404 (comme `trucks`, `drivers` du Lot 2).
- Le module `import` reste **à venir** (`UPCOMING_MODULES`) jusqu'à T46 : ses routes sont
  montées mais éteintes pour toute boutique.
"""

from collections.abc import Iterable
from dataclasses import dataclass

from app.application.attachments.ports import FileStorage
from app.application.imports.access import ImportAccess
from app.application.imports.models import ImportModel, ImportModels
from app.application.imports.previews import PreviewFiles
from app.application.imports.use_cases.download_template import DownloadImportTemplate
from app.application.imports.use_cases.preview_import import PreviewImport
from app.application.security.policy import Policy
from app.bootstrap.identity import IdentityModule
from app.infrastructure.spreadsheets.reader import TabularReader
from app.infrastructure.spreadsheets.xlsx_writer import OpenpyxlWriter
from app.interface.http.routes.import_components import ImportsComponents

MODELS: tuple[ImportModel, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class ImportsModule:
    http: ImportsComponents
    models: ImportModels
    previews: PreviewFiles


def build_imports(
    identity: IdentityModule, storage: FileStorage, models: Iterable[ImportModel] | None = None
) -> ImportsModule:
    """`models` : imposé par les tests (modèle témoin) ; sinon le registre `MODELS`."""
    clock, uows = identity.clock, identity.core.shop_uow_factory
    registry = ImportModels(MODELS if models is None else models)
    access = ImportAccess(Policy(clock=clock.now), registry)
    previews = PreviewFiles(storage)
    http = ImportsComponents(
        template=DownloadImportTemplate(uows, access, OpenpyxlWriter()),
        preview=PreviewImport(uows, access, clock, TabularReader(), previews),
        guard=identity.auth.guard,
    )
    return ImportsModule(http=http, models=registry, previews=previews)
