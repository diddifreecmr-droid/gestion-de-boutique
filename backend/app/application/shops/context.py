"""Aides communes aux cas d'utilisation du socle : boutique de l'acteur, auteur journalisé."""

from app.application.security.actor import Actor
from app.application.security.errors import role_label
from app.domain.audit.values import Performer
from app.domain.shared.errors import VersionConflict
from app.domain.shared.ids import ShopId


def actor_shop(actor: Actor) -> ShopId:
    """Boutique de l'acteur ; son absence est exclue par la `Policy` (défense en profondeur)."""
    if actor.shop_id is None:
        msg = "Action de boutique sans boutique active"
        raise RuntimeError(msg)
    return actor.shop_id


def performer_of(actor: Actor) -> Performer:
    """Auteur d'une entrée de journal : rôle **au moment de l'action** (RG-T04)."""
    return Performer(actor.user_id, role_label(actor), actor.device_id)


def require_version(current: int, expected: int) -> None:
    """Verrou optimiste demandé par le client (`PATCH` + `version`, specs § 6.1) → 409."""
    if current != expected:
        msg = "L'élément a été modifié entre-temps"
        raise VersionConflict(
            msg,
            details={"expected_version": expected, "current_version": current},
        )
