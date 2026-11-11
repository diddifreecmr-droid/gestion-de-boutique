"""Saisie d'une dépense → `ExpenseDetails` vérifiés (UC-DEP-01, UC-DEP-04 ; RG-T09, RG-T19).

Commun à `RecordExpense` et `CorrectExpense` :

- date : aujourd'hui par défaut, contrôlée par `validate_entry_date` (RG-T09) ;
- catégorie, mode de paiement, lieu : lus **dans la boutique** (autre boutique → 404) et
  actifs — sauf s'ils sont inchangés lors d'une correction (une catégorie désactivée depuis
  n'empêche pas de corriger le montant) ;
- mode de paiement absent → le premier mode actif dans l'ordre d'affichage, « Espèces » pour
  tous les profils (RG-T19, CDC § 20.6 « Espèces par défaut ») ;
- tags : choisis ou **créés à la volée** par leur nom ; un nom déjà connu (sans casse) donne le
  tag existant, un tag fusionné donne sa cible (UC-DEP-02) ;
- « Autre » exige une description (`require_description`).
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.application.expenses.ports import TagRepository
from app.application.ports.uow import UnitOfWork
from app.application.shops.ports import (
    ExpenseCategoryRepository,
    LocationRepository,
    PaymentModeRepository,
)
from app.domain.audit.values import Performer
from app.domain.expenses.details import ExpenseDetails
from app.domain.expenses.errors import InactiveReference
from app.domain.expenses.expense import require_description
from app.domain.expenses.ids import AttachmentId, TagId
from app.domain.expenses.tag import Tag, clean_tag_name, tag_key
from app.domain.shared.business_day import validate_entry_date
from app.domain.shared.errors import DateOutOfRange, ValidationFailed
from app.domain.shops.ids import ExpenseCategoryId, LocationId, PaymentModeId

MAX_TAGS = 10
CLOCK_TOLERANCE = timedelta(minutes=10)
"""Saisie datée de plus de 10 min dans le futur : horloge du téléphone fausse (Q7/Q8)."""


@dataclass(frozen=True, slots=True, kw_only=True)
class ExpenseInput:
    amount: int
    category_id: ExpenseCategoryId
    spent_on: date | None = None
    payment_mode_id: PaymentModeId | None = None
    tag_names: tuple[str, ...] = ()
    description: str | None = None
    location_id: LocationId | None = None
    beneficiary: str | None = None
    attachment_id: AttachmentId | None = None


def checked_capture_time(captured_at: datetime | None, now: datetime) -> datetime:
    """Heure de l'appareil (`X-Captured-At`) ou, à défaut, celle du serveur."""
    if captured_at is None:
        return now
    if captured_at > now + CLOCK_TOLERANCE:
        msg = "Heure du téléphone dans le futur : vérifiez son horloge"
        raise DateOutOfRange(msg, details={"captured_at": captured_at.isoformat()})
    return captured_at


class DetailsResolver:
    """Construit des `ExpenseDetails` dans l'unité de travail d'un cas d'utilisation."""

    def __init__(self, uow: UnitOfWork, performer: Performer, now: datetime) -> None:
        self._uow = uow
        self._performer = performer
        self._now = now

    def resolve(
        self,
        data: ExpenseInput,
        *,
        today: date,
        is_owner: bool,
        previous: ExpenseDetails | None = None,
    ) -> ExpenseDetails:
        spent_on = validate_entry_date(data.spent_on or today, today, is_owner=is_owner)
        category = ExpenseCategoryRepository.within(self._uow).get(data.category_id)
        unchanged = previous is not None and previous.category_id == category.id
        if not (category.active or unchanged):
            raise InactiveReference("category_id", str(category.id))
        details = ExpenseDetails(
            spent_on=spent_on,
            amount=data.amount,
            category_id=category.id,
            payment_mode_id=self._mode(data.payment_mode_id, previous),
            tag_ids=self._tags(data.tag_names),
            description=data.description,
            location_id=self._location(data.location_id, previous),
            beneficiary=data.beneficiary,
            attachment_id=data.attachment_id,
        )
        require_description(category, details)
        return details

    def _mode(
        self, mode_id: PaymentModeId | None, previous: ExpenseDetails | None
    ) -> PaymentModeId:
        modes = PaymentModeRepository.within(self._uow)
        if mode_id is None:
            active = [mode for mode in modes.list_all() if mode.details.active]
            if not active:
                msg = "Aucun mode de paiement actif dans la boutique"
                raise ValidationFailed(msg, details={"field": "payment_mode_id"})
            return active[0].id
        mode = modes.get(mode_id)
        if not mode.details.active and (previous is None or previous.payment_mode_id != mode.id):
            raise InactiveReference("payment_mode_id", str(mode.id))
        return mode.id

    def _location(
        self, location_id: LocationId | None, previous: ExpenseDetails | None
    ) -> LocationId | None:
        if location_id is None:
            return None
        location = LocationRepository.within(self._uow).get(location_id)
        if not location.active and (previous is None or previous.location_id != location.id):
            raise InactiveReference("location_id", str(location.id))
        return location.id

    def _tags(self, names: tuple[str, ...]) -> tuple[TagId, ...]:
        if len(names) > MAX_TAGS:
            msg = f"{MAX_TAGS} tags au plus par dépense"
            raise ValidationFailed(msg, details={"field": "tags", "max": MAX_TAGS})
        tags = TagRepository.within(self._uow)
        found: list[TagId] = []
        for raw in names:
            name = clean_tag_name(raw)
            tag = tags.find_by_key(tag_key(name))
            if tag is None:
                tag = Tag.create(self._uow.shop_id, name, performer=self._performer, now=self._now)
                tags.add(tag)
            found.append(tag.merged_into or tag.id)
        return tuple(found)
