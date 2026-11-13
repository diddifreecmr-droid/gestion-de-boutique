"""Contenu de départ du **nouveau** profil d'une boutique vide (QC-1, T27), dans sa transaction.

Pendant de `seeding.py` pour un changement de type (`ChangeShopProfile`) :

- lieux : plan de `domain/shops/profile_change.py` (créés, repris, inutilisés désactivés),
  chaque écriture journalisée (`LocationCreated`, `LocationChanged`) ;
- réglages : ceux du nouveau profil (reçu, largeurs, délai d'échange, lieu de réception…) ;
  le message de pied de reçu saisi par la boutique est gardé ;
- modes de paiement et catégories de dépense de base absents (par nom, sans casse) : créés.
"""

from dataclasses import dataclass, replace
from datetime import datetime

from app.application.ports.uow import UnitOfWork
from app.application.shops.ports import (
    ExpenseCategoryRepository,
    LocationRepository,
    PaymentModeRepository,
    ShopSettingsRepository,
)
from app.application.shops.seeding import default_settings
from app.domain.audit.values import Performer
from app.domain.profiles.profile import ShopProfile
from app.domain.shops.expense_category import ExpenseCategory
from app.domain.shops.ids import LocationId
from app.domain.shops.location import Location
from app.domain.shops.payment_mode import PaymentMode, PaymentModeDetails
from app.domain.shops.profile_change import plan_locations
from app.domain.shops.values import name_key


@dataclass(frozen=True, slots=True, kw_only=True)
class SwitchRequest:
    profile: ShopProfile
    in_use: frozenset[LocationId]
    performer: Performer
    now: datetime


def switch_profile_content(uow: UnitOfWork, request: SwitchRequest) -> None:
    """Écrit lieux, réglages, modes et catégories du nouveau profil (voir l'en-tête)."""
    reception = _switch_locations(uow, request)
    settings_repo = ShopSettingsRepository.within(uow)
    settings = settings_repo.current()
    values = replace(
        default_settings(request.profile, reception),
        footer_message=settings.values.footer_message,
    )
    if settings.change(values, performer=request.performer, now=request.now):
        settings_repo.update(settings)
    _add_missing_payment_modes(uow, request)
    _add_missing_categories(uow, request.profile)


def _switch_locations(uow: UnitOfWork, request: SwitchRequest) -> Location:
    repo = LocationRepository.within(uow)
    plan = plan_locations(repo.list_all(), request.profile, request.in_use)
    performer, now = request.performer, request.now
    for details in plan.created:
        repo.add(Location.create(uow.shop_id, details, performer=performer, now=now))
    for location, details in plan.changed:
        location.change(details, performer=performer, now=now)
        repo.update(location)
    wanted = name_key(request.profile.reception_location)
    found = [loc for loc in repo.list_all() if loc.name_key == wanted and loc.active]
    if len(found) != 1:  # le plan crée ou reprend toujours ce lieu : défense en profondeur
        msg = f"Lieu de réception {request.profile.reception_location!r} introuvable"
        raise RuntimeError(msg)
    return found[0]


def _add_missing_payment_modes(uow: UnitOfWork, request: SwitchRequest) -> None:
    repo = PaymentModeRepository.within(uow)
    existing = repo.list_all()
    known = {mode.name_key for mode in existing}
    order = max((mode.details.display_order for mode in existing), default=0)
    for template in request.profile.payment_modes:
        if name_key(template.name) in known:
            continue
        order += 1
        details = PaymentModeDetails(
            name=template.name,
            reference_required=template.reference_required,
            display_order=order,
        )
        mode = PaymentMode.create(
            uow.shop_id, details, performer=request.performer, now=request.now
        )
        repo.add(mode)


def _add_missing_categories(uow: UnitOfWork, profile: ShopProfile) -> None:
    repo = ExpenseCategoryRepository.within(uow)
    existing = repo.list_all()
    known = {category.name_key for category in existing}
    order = max((category.display_order for category in existing), default=0)
    for name in profile.expense_categories:
        if name_key(name) not in known:
            order += 1
            repo.add(ExpenseCategory.seed_base(uow.shop_id, name, order))
