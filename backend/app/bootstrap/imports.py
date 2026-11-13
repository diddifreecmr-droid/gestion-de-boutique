"""Assemblage de l'import (TR-22) : tableurs `openpyxl`/CSV, stockage partagé, modèles.

- Le fichier d'aperçu va dans le **même** `FileStorage` que les pièces jointes (Silo en prod).
- `import_models(identity)` : registre des modèles branchés, une ligne par modèle : Articles
  et Stock de départ (T33), Clients, Créances en cours et Fournisseurs (T34). Un modèle absent
  répond 404 (comme `trucks`, `drivers` du Lot 2).
- Le module `import` reste **à venir** (`UPCOMING_MODULES`) jusqu'à T46 : ses routes sont
  montées mais éteintes pour toute boutique.
"""

from collections.abc import Iterable
from dataclasses import dataclass

from app.application.attachments.ports import FileStorage
from app.application.imports.access import ImportAccess
from app.application.imports.kinds.articles import ArticlesImport
from app.application.imports.kinds.customers import CustomersImport
from app.application.imports.kinds.opening_stock import OpeningStockImport
from app.application.imports.kinds.receivables import ReceivablesImport
from app.application.imports.kinds.suppliers import SuppliersImport
from app.application.imports.models import ImportModel, ImportModels
from app.application.imports.previews import PreviewFiles
from app.application.imports.use_cases.cancel_import import CancelImport
from app.application.imports.use_cases.confirm_import import ConfirmImport
from app.application.imports.use_cases.download_template import DownloadImportTemplate
from app.application.imports.use_cases.preview_import import PreviewImport
from app.application.imports.use_cases.read_imports import ReadImports
from app.application.security.policy import Policy
from app.bootstrap.identity import IdentityModule
from app.infrastructure.spreadsheets.reader import TabularReader
from app.infrastructure.spreadsheets.xlsx_writer import OpenpyxlWriter
from app.interface.http.routes.import_components import ImportsComponents


def import_models(identity: IdentityModule) -> tuple[ImportModel, ...]:
    return (
        ArticlesImport(),
        OpeningStockImport(identity.clock),
        CustomersImport(),
        ReceivablesImport(identity.clock, identity.uow_factory),
        SuppliersImport(),
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ImportsModule:
    http: ImportsComponents
    models: ImportModels
    previews: PreviewFiles


def build_imports(
    identity: IdentityModule, storage: FileStorage, models: Iterable[ImportModel] | None = None
) -> ImportsModule:
    """`models` : imposé par les tests (modèle témoin) ; sinon `import_models(identity)`."""
    clock, uows = identity.clock, identity.core.shop_uow_factory
    registry = ImportModels(import_models(identity) if models is None else models)
    policy = Policy(clock=clock.now)
    access = ImportAccess(policy, registry)
    previews, reader, writer = PreviewFiles(storage), TabularReader(), OpenpyxlWriter()
    http = ImportsComponents(
        template=DownloadImportTemplate(uows, access, writer),
        preview=PreviewImport(uows, access, clock, reader, previews),
        confirm=ConfirmImport(uows, access, clock, reader, previews),
        read=ReadImports(uows, identity.uow_factory, access, writer),
        cancel=CancelImport(uows, policy, clock),
        guard=identity.auth.guard,
    )
    return ImportsModule(http=http, models=registry, previews=previews)
