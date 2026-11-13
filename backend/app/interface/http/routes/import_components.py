"""Cas d'utilisation de l'import, assemblés par la composition root (TR-22)."""

from dataclasses import dataclass

from app.application.imports.use_cases.cancel_import import CancelImport
from app.application.imports.use_cases.confirm_import import ConfirmImport
from app.application.imports.use_cases.download_template import DownloadImportTemplate
from app.application.imports.use_cases.preview_import import PreviewImport
from app.application.imports.use_cases.read_imports import ReadImports
from app.interface.http.security import AuthGuard


@dataclass(frozen=True, slots=True, kw_only=True)
class ImportsComponents:
    template: DownloadImportTemplate
    preview: PreviewImport
    confirm: ConfirmImport
    read: ReadImports
    cancel: CancelImport
    guard: AuthGuard
