"""Registre des modèles d'import (UC-IMP-01) : chaque modèle s'y branche (T33, T34).

Un modèle (`ImportModel`) déclare :

- `kind` (code de l'API), `permission` (matrice § 4.2 : `IMPORT_ARTICLES`…) et `modules`, les
  modules **en plus** de `import` qu'il exige (créances → `receivables`, fournisseurs →
  `purchases`) : éteint → 403 `MODULE_DISABLED` (IMP-11) ;
- `template(profile)` : ses colonnes, selon le profil de la boutique (Motos : marque + modèle,
  Textile : unité, longueur d'une pièce) ;
- `check(uow, actor, rows)` : contrôle **en lecture seule** des lignes déjà nettoyées
  (doublons dans le fichier ou en base, lieu inconnu…) et ce que l'import créerait
  (« 3 articles nouveaux seront créés »). Il n'écrit jamais : l'aperçu ne modifie rien (IMP-03).

`ImportModels.get(texte)` : modèle inconnu ou pas encore branché → 404 `NOT_FOUND` (IMP-02 :
`trucks`, `drivers`). Deux modèles du même `kind` : refus à l'assemblage (fail-fast).
"""

from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import ClassVar

from app.application.ports.uow import UnitOfWork
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.domain.imports.problems import RowError
from app.domain.imports.sheet import ParsedRow
from app.domain.imports.template import TemplateSpec
from app.domain.imports.values import ImportKind
from app.domain.profiles.modules import Module
from app.domain.profiles.profile import ShopProfile
from app.domain.shared.errors import NotFound


@dataclass(frozen=True, slots=True, kw_only=True)
class ModelCheck:
    """Verdict d'un modèle sur les lignes nettoyées."""

    accepted: tuple[int, ...]
    """Lignes qui seraient importées."""
    refused: tuple[RowError, ...] = ()
    """Lignes écartées par le modèle : doublon, lieu inconnu… (une ou plusieurs par ligne)."""
    notes: tuple[str, ...] = ()
    """Ce que l'import créerait : « 3 articles nouveaux seront créés »."""

    def __post_init__(self) -> None:
        if {error.line for error in self.refused} & set(self.accepted):
            msg = "Une ligne ne peut être à la fois acceptée et écartée"
            raise ValueError(msg)


class ImportModel(ABC):
    kind: ClassVar[ImportKind]
    permission: ClassVar[Permission]
    modules: ClassVar[frozenset[Module]] = frozenset()

    @abstractmethod
    def template(self, profile: ShopProfile) -> TemplateSpec:
        """Colonnes du modèle pour ce profil (`TemplateSpec.kind` = `kind`)."""

    @abstractmethod
    def check(self, uow: UnitOfWork, actor: Actor, rows: Sequence[ParsedRow]) -> ModelCheck:
        """Contrôle en lecture seule ; chaque ligne reçue est acceptée ou écartée."""


class ImportModels:
    def __init__(self, models: Iterable[ImportModel] = ()) -> None:
        self._models: dict[ImportKind, ImportModel] = {}
        for model in models:
            kind = ImportKind(model.kind)
            if kind in self._models:
                msg = f"Deux modèles d'import pour « {kind} »"
                raise ValueError(msg)
            self._models[kind] = model

    @property
    def kinds(self) -> tuple[ImportKind, ...]:
        return tuple(sorted(self._models))

    def get(self, kind: str) -> ImportModel:
        known = {member.value: member for member in ImportKind}
        model = self._models.get(known[kind]) if kind in known else None
        if model is None:
            msg = "Modèle d'import inconnu"
            raise NotFound(msg, details={"kind": kind[:64]})
        return model
