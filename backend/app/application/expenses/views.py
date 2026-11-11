"""Vues renvoyées par les cas d'utilisation des dépenses et règle « qui peut corriger ».

`ExpenseView` = la dépense, ses tags (noms lisibles) et `editable` : l'acteur peut-il encore la
corriger ou l'annuler maintenant (UC-DEP-04) ? Le frontend s'en sert pour afficher ou non les
boutons ; le serveur revérifie à chaque action (`require_correction`).

Règle UC-DEP-04 (matrice `EXPENSE_CORRECT` : propriétaire « Tout », comptable « Siens ») :

- propriétaire : toujours, tant que la dépense est valide ;
- comptable : **ses** dépenses seulement (autre auteur → 403 journalisé), et jusqu'à minuit
  (Douala) le jour de la saisie (`CORRECTION_WINDOW_CLOSED`, 422) ;
- vendeur, chauffeur, administrateur délégué (lecture seule) : jamais (403).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from app.application.expenses.ports import TagRepository
from app.application.ports.uow import UnitOfWork
from app.application.security.access import Access
from app.application.security.actor import Actor
from app.application.security.errors import PermissionDenied
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.security.role_matrix import access_for
from app.domain.expenses.expense import Expense
from app.domain.expenses.ids import TagId
from app.domain.expenses.tag import Tag


@dataclass(frozen=True, slots=True)
class ExpenseView:
    expense: Expense
    tags: tuple[Tag, ...]
    editable: bool


def require_correction(policy: Policy, actor: Actor, expense: Expense, now: datetime) -> None:
    """Lève si l'acteur ne peut pas corriger ni annuler `expense` maintenant."""
    access = policy.require(actor, Permission.EXPENSE_CORRECT)
    if access is Access.OWN and expense.capture.created_by != actor.user_id:
        raise PermissionDenied(actor, Permission.EXPENSE_CORRECT)
    expense.require_editable(by_owner=access is Access.ALL, now=now)


def can_correct(actor: Actor, expense: Expense, now: datetime) -> bool:
    """Même règle que `require_correction`, sans lever (affichage des boutons)."""
    if actor.role is None or expense.cancellation is not None:
        return False
    access = access_for(actor.role, Permission.EXPENSE_CORRECT)
    if access is Access.ALL:
        return True
    if access is Access.OWN:
        return expense.capture.created_by == actor.user_id and now < expense.correction_deadline
    return False


def tag_index(uow: UnitOfWork) -> dict[TagId, Tag]:
    return {tag.id: tag for tag in TagRepository.within(uow).list_all()}


def view_of(
    actor: Actor, expense: Expense, tags: Mapping[TagId, Tag], now: datetime
) -> ExpenseView:
    missing = [tag for tag in expense.details.tag_ids if tag not in tags]
    if missing:
        msg = f"Dépense {expense.number} : tags introuvables {missing}"
        raise RuntimeError(msg)
    return ExpenseView(
        expense=expense,
        tags=tuple(tags[tag] for tag in expense.details.tag_ids),
        editable=can_correct(actor, expense, now),
    )
