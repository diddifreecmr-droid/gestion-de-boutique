"""Garde commune des actions du propriétaire sur un membre (débloquer, code, appareils).

1. `Policy.require(actor, MEMBER_MANAGE)` : seul le propriétaire (CDC § 4.2, RG-D07) ; l'admin
   plateforme sans délégation reçoit 404, avec délégation 403 (il ne fait que consulter) ;
2. la cible doit être rattachée (même inactive) à **la boutique de l'acteur** ; sinon
   `NotFound`, comme un identifiant inexistant : un propriétaire de B n'apprend rien des
   comptes de A.

Le compte étant plateforme, l'effet (blocage levé, code, sessions) vaut pour toutes les
boutiques de l'utilisateur ; la portée par boutique reste une question ouverte (recette Q-27).
"""

from app.application.identity.ports import MembershipDirectory
from app.application.ports.repository import not_found
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.domain.shared.ids import UserId


class MemberAccess:
    def __init__(self, policy: Policy, memberships: MembershipDirectory) -> None:
        self._policy = policy
        self._memberships = memberships

    def require(self, actor: Actor, target: UserId) -> None:
        self._policy.require(actor, Permission.MEMBER_MANAGE)
        if actor.shop_id is None:  # exclu par la Policy (admin sans boutique) : défense
            msg = "Action sur un membre sans boutique active"
            raise RuntimeError(msg)
        if self._memberships.find(target, actor.shop_id) is None:
            raise not_found(target)
