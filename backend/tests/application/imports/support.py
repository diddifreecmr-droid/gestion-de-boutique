"""Modèles témoins branchés sur le registre (les vrais modèles arrivent en T33, T34).

- `WitnessArticles` (`articles`, `IMPORT_ARTICLES`) : nom et prix obligatoires, lieu (liste
  stricte), catégorie (liste indicative) ; doublon de nom dans le fichier et lieu inconnu
  écartés ; note « n articles nouveaux seront créés ».
- `WitnessReceivables` (`receivables`, `IMPORT_RECEIVABLES`) : exige le module `receivables`.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field

from app.application.imports.models import ImportModel, ModelCheck
from app.application.ports.uow import UnitOfWork
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.shops.ports import LocationRepository
from app.bootstrap.imports import ImportsModule, build_imports
from app.domain.imports.columns import ChoiceSource, ColumnKind, ColumnSpec
from app.domain.imports.problems import RowError
from app.domain.imports.sheet import ParsedRow
from app.domain.imports.template import TemplateSpec
from app.domain.imports.values import ImportKind
from app.domain.profiles.modules import Module
from app.domain.profiles.profile import ShopProfile
from app.infrastructure.storage.memory import MemoryFileStorage
from tests.application.catalog.support import CatalogWorld

NAME = ColumnSpec(key="name", header="Nom", subject="le nom", required=True, example="Chemise")
PRICE = ColumnSpec(
    key="price", header="Prix", subject="le prix", kind=ColumnKind.AMOUNT, required=True,
    example="9 000",
)  # fmt: skip
PLACE = ColumnSpec(key="location", header="Lieu", subject="le lieu", choices=ChoiceSource.LOCATIONS)
CATEGORY = ColumnSpec(
    key="category", header="Catégorie", subject="la catégorie", choices=ChoiceSource.CATEGORIES
)


class WitnessArticles(ImportModel):
    kind = ImportKind.ARTICLES
    permission = Permission.IMPORT_ARTICLES

    def template(self, profile: ShopProfile) -> TemplateSpec:
        return TemplateSpec(
            kind=self.kind,
            columns=(NAME, PRICE, PLACE, CATEGORY),
            instructions=(f"Profil : {profile.label}",),
        )

    def check(self, uow: UnitOfWork, actor: Actor, rows: Sequence[ParsedRow]) -> ModelCheck:
        places = {loc.name.casefold() for loc in LocationRepository.within(uow).list_all()}
        seen: dict[str, int] = {}
        accepted: list[int] = []
        refused: list[RowError] = []
        for row in rows:
            name, place = str(row.values["name"]), row.values["location"]
            if name.casefold() in seen:
                message = f"doublon : « {name} » figure déjà ligne {seen[name.casefold()]}"
                refused.append(RowError(row.line, None, message))
            elif isinstance(place, str) and place.casefold() not in places:
                refused.append(RowError(row.line, "Lieu", f"le lieu « {place} » est inconnu"))
            else:
                seen[name.casefold()] = row.line
                accepted.append(row.line)
        notes = (f"{len(accepted)} articles nouveaux seront créés",)
        return ModelCheck(accepted=tuple(accepted), refused=tuple(refused), notes=notes)


class WitnessReceivables(ImportModel):
    kind = ImportKind.RECEIVABLES
    permission = Permission.IMPORT_RECEIVABLES
    modules = frozenset({Module.RECEIVABLES})

    def template(self, profile: ShopProfile) -> TemplateSpec:
        return TemplateSpec(kind=self.kind, columns=(NAME, PRICE))

    def check(self, uow: UnitOfWork, actor: Actor, rows: Sequence[ParsedRow]) -> ModelCheck:
        return ModelCheck(accepted=tuple(row.line for row in rows))


WITNESSES: tuple[ImportModel, ...] = (WitnessArticles(), WitnessReceivables())


@dataclass
class ImportWorld(CatalogWorld):
    storage: MemoryFileStorage = field(default_factory=MemoryFileStorage)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.imports: ImportsModule = build_imports(self.identity, self.storage, WITNESSES)

    def table_versions(self) -> dict[str, dict[object, int]]:
        """Toutes les lignes validées de la base mémoire (preuve d'absence d'écriture)."""
        database = self.core.database
        assert database is not None
        tables = database._tables  # instantané de test, lecture seule
        return {name: {k: row.version for k, row in rows.items()} for name, rows in tables.items()}
