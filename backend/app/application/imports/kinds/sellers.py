"""« Vendeur responsable » d'une créance importée : nom ou téléphone d'un membre (T34).

Candidats : membres **actifs** de la boutique au rôle vendeur ou propriétaire (`SELLING_ROLES`,
même règle que `require_seller`, UC-CRE-02). Le nom et le téléphone viennent du compte
(plateforme), lus une fois par contrôle dans une unité de travail plateforme **en lecture
seule** (jamais validée). Un nom porté par deux membres est ambigu : la ligne demande le
téléphone.
"""

from app.application.identity.uow import IdentityUnitOfWorkFactory
from app.application.imports.verdicts import RowRefused
from app.application.ports.uow import UnitOfWork
from app.application.sales.resolver import SELLING_ROLES
from app.application.shops.ports import MembershipRepository
from app.domain.catalog.keys import fold
from app.domain.identity.phone import PhoneNumber
from app.domain.shared.errors import DomainError
from app.domain.shared.ids import UserId

SELLER = "Vendeur responsable"


class Sellers:
    def __init__(self, identity: IdentityUnitOfWorkFactory, uow: UnitOfWork) -> None:
        members = [
            m
            for m in MembershipRepository.within(uow).list_all()
            if m.active and m.role in SELLING_ROLES
        ]
        self._by_phone: dict[str, UserId] = {}
        self._by_name: dict[str, UserId | None] = {}
        if not members:
            return
        with identity() as platform:
            for member in members:
                user = platform.users.get(member.user_id)
                self._by_phone[user.phone.e164] = user.id
                key = fold(user.name)
                self._by_name[key] = None if key in self._by_name else user.id

    def resolve(self, wanted: str | None) -> UserId | None:
        """Membre désigné (`None` si la cellule est vide) ; `RowRefused` sinon."""
        if wanted is None:
            return None
        try:
            found = self._by_phone.get(PhoneNumber.parse(wanted).e164)
        except DomainError:
            found = None
        if found is not None:
            return found
        key = fold(wanted)
        if key in self._by_name:
            by_name = self._by_name[key]
            if by_name is None:
                message = f"plusieurs membres s'appellent « {wanted} » : indiquez son téléphone"
                raise RowRefused(SELLER, message)
            return by_name
        message = f"le vendeur « {wanted} » n'est pas un vendeur actif de la boutique"
        raise RowRefused(SELLER, message)
