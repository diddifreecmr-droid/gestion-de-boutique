"""Lignes du modèle Créances en cours : colonnes et contrôle d'une ligne (T34, IMP-08).

Contrôle (lecture seule) : téléphone lisible ; client connu par son téléphone, déjà créé plus
haut dans le fichier, ou **nouveau** — son nom est alors obligatoire ; montant restant dû > 0 ;
date d'origine jamais future (RG-T09, l'import des créances est réservé au propriétaire : passé
illimité) ; vendeur responsable reconnu ; doublon d'une créance ancienne déjà enregistrée
(même client, même montant, même date d'origine).
"""

from dataclasses import dataclass
from datetime import date

from app.application.imports.kinds.customers import read_phone
from app.application.imports.kinds.sellers import SELLER, Sellers
from app.application.imports.verdicts import (
    RowRefused,
    amount,
    day,
    problem_of,
    required_text,
    text,
)
from app.application.receivables.ports import ReceivableRepository
from app.application.receivables.use_cases.record_legacy import LegacyReceivableCommand
from app.application.sales.inputs import CustomerInput
from app.application.sales.ports import CustomerRepository
from app.domain.identity.phone import PhoneNumber
from app.domain.imports.columns import ColumnKind, ColumnSpec
from app.domain.imports.sheet import ParsedRow
from app.domain.receivables.values import DESCRIPTION_MAX_LENGTH, ReceivableOrigin
from app.domain.shared.business_day import validate_entry_date
from app.domain.shared.errors import DomainError
from app.domain.shared.money import Money

PHONE, AMOUNT, OPENED, NAME = (
    "Téléphone du client", "Montant restant dû", "Date d'origine", "Nom du client"
)  # fmt: skip
DEFAULT_DESCRIPTION = "Reprise par import"
COLUMNS = (
    ColumnSpec(key="phone", header=PHONE, subject="le téléphone du client", required=True,
               example="690 00 00 01"),
    ColumnSpec(key="amount", header=AMOUNT, subject="le montant restant dû",
               kind=ColumnKind.AMOUNT, required=True, example="300 000"),
    ColumnSpec(key="opened_on", header=OPENED, subject="la date d'origine",
               kind=ColumnKind.DATE, required=True, example="01/03/2026"),
    ColumnSpec(key="name", header=NAME, subject="le nom du client",
               example="Ali Bouba", help="Obligatoire si le client est nouveau."),
    ColumnSpec(key="description", header="Description", subject="la description",
               max_length=DESCRIPTION_MAX_LENGTH, example="1 moto Haojue, cahier 2026",
               help=f"« {DEFAULT_DESCRIPTION} » si vide."),
    ColumnSpec(key="seller", header=SELLER, subject="le vendeur responsable",
               help="Nom ou téléphone d'un vendeur (facultatif)."),
    ColumnSpec(key="remind_on", header="Date de rappel", subject="la date de rappel",
               kind=ColumnKind.DATE, help="Facultative ; une date future est permise."),
)  # fmt: skip


@dataclass(frozen=True, slots=True)
class LegacyLine:
    line: int
    phone: PhoneNumber
    command: LegacyReceivableCommand
    new_customer: bool
    remind_on: date | None

    @property
    def key(self) -> tuple[str, int, date]:
        return (self.phone.e164, self.command.amount, self.command.opened_on)


def _amount(row: ParsedRow) -> int:
    value = amount(row, "amount")
    if value is None or value <= 0:
        message = "le montant restant dû doit être supérieur à 0"
        raise RowRefused(AMOUNT, message)
    return value


def _opened_on(row: ParsedRow, today: date) -> date:
    wanted = day(row, "opened_on")
    if wanted is None:
        msg = "Date d'origine obligatoire vide après nettoyage"
        raise RuntimeError(msg)
    try:
        return validate_entry_date(wanted, today, is_owner=True)
    except DomainError as error:
        message = f"la date d'origine : {problem_of(error)}"
        raise RowRefused(OPENED, message) from error


def plan_line(
    row: ParsedRow,
    today: date,
    sellers: Sellers,
    customers: CustomerRepository,
    receivables: ReceivableRepository,
    new_phones: dict[str, str],
) -> LegacyLine:
    phone = read_phone(required_text(row, "phone"), PHONE)
    name, total, opened_on = text(row, "name"), _amount(row), _opened_on(row, today)
    holder = customers.find_by_phone(phone)
    new_customer = holder is None and phone.e164 not in new_phones
    if new_customer and name is None:
        message = "le nom du client est vide : ce téléphone n'est pas celui d'un client connu"
        raise RowRefused(NAME, message)
    if holder is not None:
        for known in receivables.for_customer(holder.id):
            same = (known.initial_amount, known.opened_on) == (Money(total), opened_on)
            if known.origin is ReceivableOrigin.LEGACY and same:
                message = f"doublon : créance ancienne déjà enregistrée pour « {holder.name} »"
                raise RowRefused(None, message)
    known_name = holder.name if holder is not None else new_phones.get(phone.e164)
    command = LegacyReceivableCommand(
        customer=CustomerInput(name=name or known_name, phone=phone.e164),
        amount=total,
        opened_on=opened_on,
        description=text(row, "description") or DEFAULT_DESCRIPTION,
        responsible_seller_id=sellers.resolve(text(row, "seller")),
    )
    return LegacyLine(row.line, phone, command, new_customer, day(row, "remind_on"))
