"""Vue d'un membre pour l'écran « Utilisateurs » du propriétaire (UC-SOC-04).

Assemble le rattachement (boutique) et le compte (plateforme) : nom, téléphone, rôle, lieu
habituel, actif dans la boutique, compte bloqué (UC-SOC-02 : le propriétaire peut débloquer),
code provisoire pas encore changé.
"""

from dataclasses import dataclass
from datetime import datetime

from app.domain.identity.status import UserStatus
from app.domain.identity.user import User
from app.domain.shops.membership import Membership


@dataclass(frozen=True, slots=True, kw_only=True)
class MemberView:
    membership: Membership
    name: str
    phone: str
    locked: bool
    must_change_pin: bool


def member_view(membership: Membership, user: User, now: datetime) -> MemberView:
    if user.id != membership.user_id:
        msg = "Compte et rattachement de deux utilisateurs différents"
        raise ValueError(msg)
    return MemberView(
        membership=membership,
        name=user.name,
        phone=user.phone.e164,
        locked=user.status_at(now) is UserStatus.LOCKED,
        must_change_pin=user.must_change_pin,
    )
