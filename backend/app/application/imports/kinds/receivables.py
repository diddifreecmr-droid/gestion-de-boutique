"""Modèle d'import **Créances en cours** (T34, CDC § 15.1 ; IMP-08, IMP-11).

Colonnes : Téléphone du client *, Montant restant dû *, Date d'origine *, Nom du client (si
nouveau), Description, Vendeur responsable, Date de rappel. Propriétaire seul
(`IMPORT_RECEIVABLES`) ; exige le module `receivables` (éteint → 403 `MODULE_DISABLED`).

Chaque ligne acceptée devient une **créance ancienne** par le cas d'utilisation existant
(`open_legacy`, UC-CRE-02) : client retrouvé par son téléphone, sinon **créé** avec le nom de la
ligne (sans nom → erreur de ligne) ; un client nouveau cité sur plusieurs lignes n'est créé
qu'une fois. Montant > 0, date d'origine jamais future, description par défaut « Reprise par
import », rappel facultatif (date future permise). Doublon : même client, même montant, même
date d'origine (dans le fichier, ou créance ancienne déjà enregistrée) → signalé et ignoré.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from app.application.identity.uow import IdentityUnitOfWorkFactory
from app.application.imports.kinds.customers import customers_note
from app.application.imports.kinds.receivable_rows import COLUMNS, LegacyLine, plan_line
from app.application.imports.kinds.sellers import Sellers
from app.application.imports.models import ImportModel, ImportRun, ModelCheck
from app.application.imports.verdicts import RowRefused, Verdict, created_note, require_first
from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWork
from app.application.receivables.ports import ReceivableRepository
from app.application.receivables.use_cases.record_legacy import open_legacy
from app.application.sales.ports import CustomerRepository
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.domain.imports.batch import ImportedItem
from app.domain.imports.sheet import ParsedRow
from app.domain.imports.template import TemplateSpec
from app.domain.imports.values import ImportedEntity, ImportKind
from app.domain.profiles.modules import Module
from app.domain.profiles.profile import ShopProfile
from app.domain.receivables.follow_up import Reminder
from app.domain.receivables.ids import ReminderId

INSTRUCTIONS = (
    "Une créance par ligne : le reste dû aujourd'hui, pas le montant d'origine.",
    "Client inconnu : indiquez son nom, il sera créé.",
    "Vendeur responsable : nom ou téléphone d'un vendeur de la boutique (facultatif).",
)


def receivables_note(count: int) -> str | None:
    return created_note(
        count, "créance ancienne sera reprise", "créances anciennes seront reprises"
    )


@dataclass(frozen=True, slots=True)
class _Plan:
    verdict: Verdict
    lines: list[LegacyLine]
    new_customers: int


class ReceivablesImport(ImportModel):
    kind = ImportKind.RECEIVABLES
    permission = Permission.IMPORT_RECEIVABLES
    modules = frozenset({Module.RECEIVABLES})

    def __init__(self, clock: Clock, identity: IdentityUnitOfWorkFactory) -> None:
        self._clock = clock
        self._identity = identity

    def template(self, profile: ShopProfile) -> TemplateSpec:
        return TemplateSpec(kind=self.kind, columns=COLUMNS, instructions=INSTRUCTIONS)

    def _plan(self, uow: UnitOfWork, rows: Sequence[ParsedRow], today: date) -> _Plan:
        customers = CustomerRepository.within(uow)
        receivables = ReceivableRepository.within(uow)
        sellers = Sellers(self._identity, uow)
        verdict, lines = Verdict(), []
        seen: dict[tuple[str, int, date], int] = {}
        new_phones: dict[str, str] = {}
        for row in rows:
            try:
                line = plan_line(row, today, sellers, customers, receivables, new_phones)
                require_first(seen, line.key, None, "la même créance")
            except RowRefused as refused:
                verdict.refuse(row.line, refused.column, refused.message)
                continue
            seen[line.key] = row.line
            if line.new_customer and line.command.customer.name is not None:
                new_phones[line.phone.e164] = line.command.customer.name
            verdict.accept(row.line)
            lines.append(line)
        return _Plan(verdict, lines, len(new_phones))

    def check(self, uow: UnitOfWork, actor: Actor, rows: Sequence[ParsedRow]) -> ModelCheck:
        plan = self._plan(uow, rows, self._clock.today())
        return plan.verdict.check(
            receivables_note(len(plan.lines)), customers_note(plan.new_customers)
        )

    def apply(
        self, uow: UnitOfWork, actor: Actor, rows: Sequence[ParsedRow], run: ImportRun
    ) -> tuple[ImportedItem, ...]:
        plan = self._plan(uow, rows, run.today)
        plan.verdict.require_all_accepted(rows)
        receivables, items = ReceivableRepository.within(uow), []
        for line in plan.lines:
            receivable = open_legacy(uow, actor, line.command, now=run.now, today=run.today)
            if line.new_customer:
                items.append(
                    ImportedItem(line.line, ImportedEntity.CUSTOMER, receivable.customer_id.value)
                )
            if line.remind_on is not None:
                reminder = Reminder(
                    id=ReminderId.new(), remind_on=line.remind_on, created_by=actor.user_id,
                    created_at=run.now,
                )  # fmt: skip
                receivable.add_reminder(reminder, performer=run.performer)
            receivables.add(receivable)
            items.append(ImportedItem(line.line, ImportedEntity.RECEIVABLE, receivable.id.value))
        return tuple(items)
