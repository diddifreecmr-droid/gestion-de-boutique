"""`GET /me` : l'utilisateur connecté, ses boutiques et son rôle dans chacune (specs § 6.3).

Seuls les rattachements **actifs** sont listés (UC-SOC-03 : liste des boutiques). Répond même
si le code provisoire n'a pas encore été changé (AUTH-02) : le client y lit `must_change_pin`.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from app.application.identity.ports import MembershipDirectory, MembershipView
from app.application.identity.uow import IdentityUnitOfWorkFactory
from app.application.identity.use_cases.authenticate import AuthenticatedUser
from app.domain.shared.ids import UserId


@dataclass(frozen=True, slots=True, kw_only=True)
class MeView:
    user_id: UserId
    name: str
    phone: str
    is_platform_admin: bool
    must_change_pin: bool
    shops: Sequence[MembershipView]


class GetMe:
    def __init__(
        self, uow_factory: IdentityUnitOfWorkFactory, memberships: MembershipDirectory
    ) -> None:
        self._uow_factory = uow_factory
        self._memberships = memberships

    def execute(self, identity: AuthenticatedUser) -> MeView:
        with self._uow_factory() as uow:
            user = uow.users.get(identity.user_id)
        shops = [m for m in self._memberships.for_user(user.id) if m.active]
        return MeView(
            user_id=user.id,
            name=user.name,
            phone=user.phone.e164,
            is_platform_admin=user.is_platform_admin,
            must_change_pin=user.must_change_pin,
            shops=tuple(shops),
        )
