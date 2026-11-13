"""Contenu d'un modèle à écrire : description du modèle et listes déroulantes résolues.

`ChoiceList.strict` : une liste stricte (lieux, types de client) refuse dans Excel toute
valeur hors liste ; une liste indicative (catégories, texte libre) avertit seulement.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from app.domain.imports.columns import ChoiceSource
from app.domain.imports.template import TemplateSpec

LIST_MAX = 500
"""Valeurs au plus par liste déroulante (au-delà, la liste est tronquée, jamais en erreur)."""


@dataclass(frozen=True, slots=True, kw_only=True)
class ChoiceList:
    source: ChoiceSource
    title: str
    values: tuple[str, ...]
    strict: bool

    def __post_init__(self) -> None:
        if len(self.values) > LIST_MAX or len(set(self.values)) != len(self.values):
            msg = f"Liste {self.source} : {LIST_MAX} valeurs distinctes au plus"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True, kw_only=True)
class TemplateWorkbook:
    spec: TemplateSpec
    lists: Mapping[ChoiceSource, ChoiceList] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        wanted = {c.choices for c in self.spec.columns if c.choices is not None}
        if wanted != set(self.lists):
            msg = f"Listes du modèle {self.spec.kind} : attendu {sorted(wanted)}"
            raise ValueError(msg)
