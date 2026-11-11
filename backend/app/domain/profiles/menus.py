"""Menus par rôle (CDC § 17.4, § 18.5, § 19.5) : **5 entrées au plus** en bas d'écran.

Une entrée « Plus » regroupe les suivantes (`children`). Le code d'entrée est stable (le
frontend y associe route et icône) ; `module` permet de masquer une entrée dont le module est
désactivé pour la boutique. Plus de 5 entrées → `ValueError` dès l'import (erreur de profil).
"""

from collections.abc import Sequence
from dataclasses import dataclass

from app.domain.profiles.modules import Module

MAX_MENU_ENTRIES = 5


@dataclass(frozen=True, slots=True)
class MenuEntry:
    code: str
    label: str
    module: Module
    children: tuple["MenuEntry", ...] = ()

    def __post_init__(self) -> None:
        if not self.code or not self.label:
            msg = "Une entrée de menu a un code et un libellé"
            raise ValueError(msg)
        if any(child.children for child in self.children):
            msg = f"Menu {self.code} : un seul niveau de sous-entrées"
            raise ValueError(msg)


def menu(*entries: MenuEntry) -> tuple[MenuEntry, ...]:
    """Menu validé : de 1 à `MAX_MENU_ENTRIES` entrées, codes uniques."""
    if not 1 <= len(entries) <= MAX_MENU_ENTRIES:
        msg = f"Un menu compte de 1 à {MAX_MENU_ENTRIES} entrées, reçu {len(entries)}"
        raise ValueError(msg)
    codes = [code for entry in entries for code in _codes(entry)]
    if len(codes) != len(set(codes)):
        msg = f"Codes de menu en double : {sorted(codes)}"
        raise ValueError(msg)
    return entries


def _codes(entry: MenuEntry) -> Sequence[str]:
    return [entry.code, *(child.code for child in entry.children)]


def entry(code: str, label: str, module: Module, *children: MenuEntry) -> MenuEntry:
    return MenuEntry(code, label, module, tuple(children))
