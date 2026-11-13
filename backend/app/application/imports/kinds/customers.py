"""Modèle d'import **Clients** (T34, CDC § 15.1 ; IMP-08).

Colonnes : Nom *, Téléphone *, Type (Particulier / Entreprise), Ville, Adresse, Plafond de
crédit, Note. Propriétaire seul (`IMPORT_CUSTOMERS` ; comptable → 403, RG-D03).

Doublon = **même téléphone** (normalisé E.164) : déjà client de la boutique, ou déjà plus haut
dans le fichier → signalé et ignoré. Écriture : `Customer.create` (journal « Créer »), une fiche
par ligne acceptée (`ImportedEntity.CUSTOMER`).
"""

from collections.abc import Sequence

from app.application.imports.choices import CUSTOMER_KIND_LABELS
from app.application.imports.models import ImportModel, ImportRun, ModelCheck
from app.application.imports.verdicts import (
    RowRefused,
    Verdict,
    amount,
    created_note,
    problem_of,
    require_first,
    required_text,
    text,
)
from app.application.ports.uow import UnitOfWork
from app.application.sales.ports import CustomerRepository
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.domain.identity.phone import PhoneNumber
from app.domain.imports.batch import ImportedItem
from app.domain.imports.columns import ChoiceSource, ColumnKind, ColumnSpec
from app.domain.imports.sheet import ParsedRow, fold_header
from app.domain.imports.template import TemplateSpec
from app.domain.imports.values import ImportedEntity, ImportKind
from app.domain.profiles.profile import ShopProfile
from app.domain.sales.customer import Customer, CustomerDetails, CustomerKind
from app.domain.shared.errors import DomainError
from app.domain.shared.money import Money

PHONE = "Téléphone"
COLUMNS = (
    ColumnSpec(key="name", header="Nom", subject="le nom", required=True, example="Ali Bouba"),
    ColumnSpec(key="phone", header=PHONE, subject="le téléphone", required=True,
               example="690 00 00 01", help="Numéro camerounais à 9 chiffres ou +237…"),
    ColumnSpec(key="kind", header="Type", subject="le type", choices=ChoiceSource.CUSTOMER_KINDS,
               example="Particulier", help="Particulier si vide."),
    ColumnSpec(key="city", header="Ville", subject="la ville", example="Garoua"),
    ColumnSpec(key="address", header="Adresse", subject="l'adresse"),
    ColumnSpec(key="credit_limit", header="Plafond de crédit", subject="le plafond de crédit",
               kind=ColumnKind.AMOUNT, help="FCFA entiers (facultatif)."),
    ColumnSpec(key="note", header="Note", subject="la note", max_length=500),
)  # fmt: skip
INSTRUCTIONS = ("Un client par ligne ; un téléphone déjà connu de la boutique est ignoré.",)
_KINDS = {fold_header(label): kind for label, kind in CUSTOMER_KIND_LABELS.items()}


def read_phone(value: str, column: str = PHONE) -> PhoneNumber:
    try:
        return PhoneNumber.parse(value)
    except DomainError as error:
        raise RowRefused(column, f"le téléphone : {problem_of(error)}") from error


def read_kind(value: str | None) -> CustomerKind:
    if value is None:
        return CustomerKind.INDIVIDUAL
    kind = _KINDS.get(fold_header(value))
    if kind is None:
        raise RowRefused("Type", "le type : « Particulier » ou « Entreprise » attendu")
    return kind


def _require_unknown(customers: CustomerRepository, phone: PhoneNumber) -> None:
    holder = customers.find_by_phone(phone)
    if holder is not None:
        message = f"doublon : le {phone.e164} est déjà celui du client « {holder.name} »"
        raise RowRefused(PHONE, message)


def customers_note(count: int) -> str | None:
    return created_note(count, "client nouveau sera créé", "clients nouveaux seront créés")


class CustomersImport(ImportModel):
    kind = ImportKind.CUSTOMERS
    permission = Permission.IMPORT_CUSTOMERS

    def template(self, profile: ShopProfile) -> TemplateSpec:
        return TemplateSpec(kind=self.kind, columns=COLUMNS, instructions=INSTRUCTIONS)

    @staticmethod
    def _details(row: ParsedRow) -> CustomerDetails:
        phone = read_phone(required_text(row, "phone"))
        kind = read_kind(text(row, "kind"))
        limit = amount(row, "credit_limit")
        try:
            return CustomerDetails(
                name=required_text(row, "name"), phone=phone, kind=kind, city=text(row, "city"),
                address=text(row, "address"), note=text(row, "note"),
                credit_limit=None if limit is None else Money(limit),
            )  # fmt: skip
        except DomainError as error:
            raise RowRefused(None, problem_of(error)) from error

    def _plan(
        self, uow: UnitOfWork, rows: Sequence[ParsedRow]
    ) -> tuple[Verdict, list[tuple[int, CustomerDetails]]]:
        customers = CustomerRepository.within(uow)
        verdict, planned, seen = Verdict(), [], dict[str, int]()
        for row in rows:
            try:
                details = self._details(row)
                phone = details.phone.e164
                _require_unknown(customers, details.phone)
                require_first(seen, phone, PHONE, f"le {phone}")
            except RowRefused as refused:
                verdict.refuse(row.line, refused.column, refused.message)
                continue
            seen[phone] = row.line
            verdict.accept(row.line)
            planned.append((row.line, details))
        return verdict, planned

    def check(self, uow: UnitOfWork, actor: Actor, rows: Sequence[ParsedRow]) -> ModelCheck:
        verdict, planned = self._plan(uow, rows)
        return verdict.check(customers_note(len(planned)))

    def apply(
        self, uow: UnitOfWork, actor: Actor, rows: Sequence[ParsedRow], run: ImportRun
    ) -> tuple[ImportedItem, ...]:
        verdict, planned = self._plan(uow, rows)
        verdict.require_all_accepted(rows)
        customers, items = CustomerRepository.within(uow), []
        for line, details in planned:
            customer = Customer.create(uow.shop_id, details, performer=run.performer, now=run.now)
            customers.add(customer)
            items.append(ImportedItem(line, ImportedEntity.CUSTOMER, customer.id.value))
        return tuple(items)
