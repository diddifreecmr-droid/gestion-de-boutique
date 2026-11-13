"""Modèle d'import **Fournisseurs** (T34, CDC § 15.1 ; IMP-11).

Colonnes : Nom *, Téléphone, Ville, Pays, Note. Propriétaire et comptable
(`IMPORT_SUPPLIERS`) ; exige le module `purchases` (éteint → 403 `MODULE_DISABLED`).

Doublon = **même nom** (sans casse, espaces réduites, comme l'unicité des fournisseurs) : déjà
fournisseur de la boutique (actif ou non), ou déjà plus haut dans le fichier → signalé et
ignoré. Écriture : `Supplier.create` (journal « Créer »), `ImportedEntity.SUPPLIER`.
"""

from collections.abc import Sequence

from app.application.imports.models import ImportModel, ImportRun, ModelCheck
from app.application.imports.verdicts import (
    RowRefused,
    Verdict,
    created_note,
    problem_of,
    require_first,
    required_text,
    text,
)
from app.application.ports.uow import UnitOfWork
from app.application.purchasing.ports import SupplierRepository
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.domain.imports.batch import ImportedItem
from app.domain.imports.columns import ColumnSpec
from app.domain.imports.sheet import ParsedRow
from app.domain.imports.template import TemplateSpec
from app.domain.imports.values import ImportedEntity, ImportKind
from app.domain.profiles.modules import Module
from app.domain.profiles.profile import ShopProfile
from app.domain.purchasing.supplier import Supplier, SupplierDetails
from app.domain.shared.errors import DomainError
from app.domain.shops.values import name_key

COLUMNS = (
    ColumnSpec(key="name", header="Nom", subject="le nom", required=True,
               example="Ets Haojue Douala"),
    ColumnSpec(key="phone", header="Téléphone", subject="le téléphone", example="699 00 00 01"),
    ColumnSpec(key="city", header="Ville", subject="la ville", example="Douala"),
    ColumnSpec(key="country", header="Pays", subject="le pays", example="Cameroun"),
    ColumnSpec(key="note", header="Note", subject="la note", max_length=500),
)  # fmt: skip
INSTRUCTIONS = ("Un fournisseur par ligne ; un nom déjà connu de la boutique est ignoré.",)


def _require_unknown(known: dict[str, str], key: str) -> None:
    if key in known:
        message = f"doublon : le fournisseur « {known[key]} » existe déjà"
        raise RowRefused("Nom", message)


def suppliers_note(count: int) -> str | None:
    return created_note(
        count, "fournisseur nouveau sera créé", "fournisseurs nouveaux seront créés"
    )


class SuppliersImport(ImportModel):
    kind = ImportKind.SUPPLIERS
    permission = Permission.IMPORT_SUPPLIERS
    modules = frozenset({Module.PURCHASES})

    def template(self, profile: ShopProfile) -> TemplateSpec:
        return TemplateSpec(kind=self.kind, columns=COLUMNS, instructions=INSTRUCTIONS)

    @staticmethod
    def _details(row: ParsedRow) -> SupplierDetails:
        try:
            return SupplierDetails(
                name=required_text(row, "name"), phone=text(row, "phone"),
                city=text(row, "city"), country=text(row, "country"), note=text(row, "note"),
            )  # fmt: skip
        except DomainError as error:
            raise RowRefused(None, problem_of(error)) from error

    def _plan(
        self, uow: UnitOfWork, rows: Sequence[ParsedRow]
    ) -> tuple[Verdict, list[tuple[int, SupplierDetails]]]:
        known = {s.name_key: s.name for s in SupplierRepository.within(uow).list_all()}
        verdict, planned, seen = Verdict(), [], dict[str, int]()
        for row in rows:
            try:
                details = self._details(row)
                key = name_key(details.name)
                _require_unknown(known, key)
                require_first(seen, key, "Nom", f"« {details.name} »")
            except RowRefused as refused:
                verdict.refuse(row.line, refused.column, refused.message)
                continue
            seen[key] = row.line
            verdict.accept(row.line)
            planned.append((row.line, details))
        return verdict, planned

    def check(self, uow: UnitOfWork, actor: Actor, rows: Sequence[ParsedRow]) -> ModelCheck:
        verdict, planned = self._plan(uow, rows)
        return verdict.check(suppliers_note(len(planned)))

    def apply(
        self, uow: UnitOfWork, actor: Actor, rows: Sequence[ParsedRow], run: ImportRun
    ) -> tuple[ImportedItem, ...]:
        verdict, planned = self._plan(uow, rows)
        verdict.require_all_accepted(rows)
        suppliers, items = SupplierRepository.within(uow), []
        for line, details in planned:
            supplier = Supplier.create(uow.shop_id, details, performer=run.performer, now=run.now)
            suppliers.add(supplier)
            items.append(ImportedItem(line, ImportedEntity.SUPPLIER, supplier.id.value))
        return tuple(items)
