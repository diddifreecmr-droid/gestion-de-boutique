"""Traduction des événements de l'identité en entrées de journal (RG-T01, UC-JRN-03, Q-23).

Les `IdentityEvent` n'ont pas de `shop_id` (un compte est plateforme). Règle d'inscription :

- action de l'utilisateur **sur lui-même** (connexion, échec, déconnexion, code changé) →
  une entrée dans **chaque boutique où il est rattaché** (UC-JRN-03 : « ses connexions ») ;
- action d'un tiers `by` (propriétaire : déblocage, code provisoire, désactivation,
  déconnexion à distance) → seulement dans les boutiques où **les deux** sont rattachés.

Câblage (T10) : `identity_audit_entries` est pur (aucune écriture) ; le handler
`IdentityAuditRecorder` (`identity_recorder.py`) l'appelle au `commit()` de l'unité plateforme
et inscrit chaque entrée par une unité de boutique **jointe** (même transaction que l'action
de l'identité, TR-09) : l'action et sa trace sont validées ensemble, ou pas du tout. Les
rattachements sont lus dans l'état validé (aucune action de l'identité n'en crée).
"""

from collections.abc import Callable
from datetime import datetime

from app.application.identity.ports import MembershipDirectory
from app.domain.audit.entry import AuditEntry, AuditRecord
from app.domain.audit.events import UnauditedEvent
from app.domain.audit.values import AuditAction, EntityRef, FieldChange, Performer
from app.domain.identity import events as ev
from app.domain.shared.ids import ShopId, UserId

MODULE = "identity"
_SENSITIVE_REVOCATIONS = {ev.RevocationReason.REMOTE, ev.RevocationReason.REFRESH_REUSE}

type _Spec = tuple[AuditAction, str, tuple[FieldChange, ...], bool]


def _spec(event: ev.IdentityEvent) -> _Spec:
    """(action, résumé, changements, sensible) de chaque événement de l'identité."""
    match event:
        case ev.LoginSucceeded():
            return AuditAction.LOGIN, "Connexion", (), False
        case ev.LoginFailed(failed_attempts=n):
            change = FieldChange("failed_attempts", n - 1, n)
            return AuditAction.LOGIN, "Échec de connexion", (change,), False
        case ev.UserLocked(locked_until=until):
            change = FieldChange("locked_until", None, until.isoformat())
            return AuditAction.UPDATE, "Compte bloqué après 5 essais", (change,), True
        case ev.UserUnlocked():
            return (
                AuditAction.UPDATE,
                "Compte débloqué",
                (FieldChange("locked", True, False),),
                True,
            )
        case ev.PinChanged():
            return AuditAction.UPDATE, "Code changé", (FieldChange("pin", None, None),), False
        case ev.PinChangeFailed(failed_attempts=n):
            change = FieldChange("pin_change_failed_attempts", n - 1, n)
            return AuditAction.UPDATE, "Échec du changement de code", (change,), False
        case ev.PinChangeLockedEvent(locked_until=until):
            change = FieldChange("pin_change_locked_until", None, until.isoformat())
            return AuditAction.UPDATE, "Changement de code bloqué 15 min", (change,), True
        case ev.PinReset():
            change = FieldChange("pin", None, None)
            return AuditAction.UPDATE, "Code provisoire attribué", (change,), True
        case ev.UserDisabled():
            return (
                AuditAction.UPDATE,
                "Compte désactivé",
                (FieldChange("active", True, False),),
                True,
            )
        case ev.UserReactivated():
            return (
                AuditAction.UPDATE,
                "Compte réactivé",
                (FieldChange("active", False, True),),
                True,
            )
        case ev.SessionRevokedEvent(reason=reason):
            change = FieldChange("reason", None, reason.value)
            sensitive = reason in _SENSITIVE_REVOCATIONS
            return AuditAction.LOGOUT, "Déconnexion", (change,), sensitive
    msg = f"{type(event).__name__} : traduction de journal manquante"
    raise UnauditedEvent(msg)


def performer_id(event: ev.IdentityEvent) -> UserId:
    """Auteur de l'action : le tiers `by` s'il y en a un, sinon l'utilisateur lui-même."""
    by = getattr(event, "by", None)
    return by if isinstance(by, UserId) else event.user_id


def identity_record(event: ev.IdentityEvent, role: Callable[[UserId], str]) -> AuditRecord:
    """Entrée d'un événement pour une boutique ; `role(user)` = rôle de l'auteur dans celle-ci."""
    action, summary, changes, sensitive = _spec(event)
    author = performer_id(event)
    device = getattr(event, "device_id", None) if author == event.user_id else None
    return AuditRecord(
        performer=Performer(author, role(author), device),
        action=action,
        entity=EntityRef("user", event.user_id.value),
        module=MODULE,
        summary=summary,
        changes=changes,
        sensitive=sensitive,
        captured_at=event.occurred_at,
    )


def identity_audit_entries(
    event: ev.IdentityEvent, memberships: MembershipDirectory, received_at: datetime
) -> list[AuditEntry]:
    """Une entrée par boutique concernée (règle d'inscription du module), triée par boutique."""
    author = performer_id(event)
    roles: dict[ShopId, dict[UserId, str]] = {}
    for view in memberships.for_user(event.user_id):
        roles.setdefault(view.shop_id, {})[event.user_id] = view.role.value
    if author != event.user_id:
        for shop_id in list(roles):
            membership = memberships.find(author, shop_id)
            if membership is None:
                del roles[shop_id]
            else:
                roles[shop_id][author] = membership.role.value
    return [
        AuditEntry.inscribe(
            shop_id,
            identity_record(event, known.__getitem__),
            received_at=received_at,
            default_captured_at=event.occurred_at,
        )
        for shop_id, known in sorted(roles.items(), key=lambda item: item[0].value)
    ]
