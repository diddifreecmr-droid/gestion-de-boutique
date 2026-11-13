"""Raccourcis de longueur du profil servis par `GET /profile` (RG-X05, T31)."""

from app.domain.profiles.profile import ProfileCode
from app.domain.profiles.textile import SaleShortcut, shortcuts_for
from app.interface.http.schemas.shop import SaleShortcutResponse


def _shortcut(shortcut: SaleShortcut) -> SaleShortcutResponse:
    length, yards = shortcut.length_m, shortcut.yards
    return SaleShortcutResponse(
        code=shortcut.code,
        label=shortcut.label,
        basis=shortcut.basis.value,
        length_m=None if length is None else str(length),
        yards=None if yards is None else str(yards),
    )


def sale_shortcuts(code: ProfileCode) -> list[SaleShortcutResponse]:
    return [_shortcut(item) for item in shortcuts_for(code)]
