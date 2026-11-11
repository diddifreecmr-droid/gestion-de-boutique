"""Un compte de boutique n'est utilisable que s'il lui reste un rattachement utilisable (RG-D06).

La désactivation vaut **par boutique** (décision T10, recette Q-27) : le propriétaire de B
désactive le rattachement de U à B, pas le compte de U dans A. Un compte dont **aucun**
rattachement n'est utilisable (tous désactivés, ou boutiques fermées) ne peut plus se
connecter ni rafraîchir sa session : « Compte désactivé, contactez le propriétaire »
(`AccountDisabled`, 403). L'administrateur plateforme n'a pas de rattachement : non concerné.
"""

from app.application.identity.ports import MembershipDirectory
from app.domain.identity.errors import AccountDisabled
from app.domain.identity.user import User


def require_reachable(memberships: MembershipDirectory, user: User) -> None:
    """Lève `AccountDisabled` si `user` (hors admin) n'a plus aucun rattachement utilisable."""
    if user.is_platform_admin:
        return
    if not any(view.usable for view in memberships.for_user(user.id)):
        raise AccountDisabled
