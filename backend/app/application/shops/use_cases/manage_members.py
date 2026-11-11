"""UC-SOC-04 — Gérer les utilisateurs de la boutique (propriétaire ; recette MEM-01 à 04, SEC-X).

- **Ajouter** : nom, téléphone, rôle (proposé par le profil), lieu habituel pour un vendeur
  (point de vente actif, MEM-01). Téléphone inconnu → compte créé avec un code provisoire
  renvoyé **une seule fois** ; téléphone connu → le compte existant est rattaché, son nom et
  son code restent les siens (ERR-DUP-05, Q-27) ; déjà membre → 409 `DUPLICATE`.
- **Modifier** (`version` du rattachement) : rôle, lieu habituel, désactiver / réactiver.
- **Portée de la désactivation (RG-D06, décision T10, Q-27)** : elle vise le **rattachement à
  cette boutique**. Le propriétaire de B ne peut pas couper l'accès de U à sa boutique A (B n'a
  aucune autorité sur A, et l'isolation interdit qu'un acte de B modifie A). U ne voit plus B
  (403 `ACCOUNT_DISABLED` sur ses routes) ; s'il ne lui reste **aucun** rattachement utilisable,
  il ne peut plus se connecter ni rafraîchir sa session (« Compte désactivé, contactez le
  propriétaire »). Débloquer, redonner un code, déconnecter les appareils agissent, eux, sur le
  compte entier (décision client du 11/11/2026, `application/identity/use_cases`).
- **RG-D08** : le dernier propriétaire actif ne peut être ni désactivé ni rétrogradé
  (`LAST_ACTIVE_OWNER`) ; la boutique est réécrite pour sérialiser deux retraits concurrents.
"""

from dataclasses import dataclass

from app.application.identity.ports import PasswordHasher, TemporaryPinGenerator
from app.application.identity.temporary_pins import draw_temporary_pin
from app.application.identity.uow import IdentityUnitOfWorkFactory
from app.application.ports.clock import Clock
from app.application.ports.repository import not_found
from app.application.ports.uow import UnitOfWork
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop, performer_of, require_version
from app.application.shops.ports import LocationRepository, MembershipRepository, ShopRepository
from app.application.shops.use_cases.member_views import MemberView, member_view
from app.domain.identity.phone import PhoneNumber
from app.domain.identity.user import User
from app.domain.profiles.registry import profile_for
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.ids import UserId
from app.domain.shared.roles import Role
from app.domain.shops.errors import LastActiveOwner
from app.domain.shops.ids import LocationId
from app.domain.shops.location import Location
from app.domain.shops.membership import Membership


@dataclass(frozen=True, slots=True, kw_only=True)
class AddMemberCommand:
    name: str
    phone: str
    role: Role
    default_location_id: LocationId | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class AddedMember:
    member: MemberView
    temporary_pin: str | None
    """Code provisoire du compte créé ; `None` si le compte existait (son code reste le sien)."""


@dataclass(frozen=True, slots=True, kw_only=True)
class UpdateMemberCommand:
    version: int
    role: Role | None = None
    default_location_id: LocationId | None = None
    location_given: bool = False
    """Vrai si `default_location_id` a été fourni (même `None`)."""
    active: bool | None = None


def _location(uow: UnitOfWork, location_id: LocationId | None) -> Location | None:
    return None if location_id is None else LocationRepository.within(uow).get(location_id)


class ManageMembers:
    def __init__(
        self,
        uow_factory: IdentityUnitOfWorkFactory,
        policy: Policy,
        hasher: PasswordHasher,
        pins: TemporaryPinGenerator,
        clock: Clock,
    ) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._hasher = hasher
        self._pins = pins
        self._clock = clock

    def list(self, actor: Actor) -> list[MemberView]:
        self._policy.require(actor, Permission.MEMBER_MANAGE)
        now = self._clock.now()
        with self._uow_factory() as uow:
            with uow.join_shop(actor_shop(actor)) as shop_uow:
                memberships = MembershipRepository.within(shop_uow).list_all()
            return [member_view(m, uow.users.get(m.user_id), now) for m in memberships]

    def add(self, actor: Actor, command: AddMemberCommand) -> AddedMember:
        self._policy.require(actor, Permission.MEMBER_MANAGE)
        phone, now = PhoneNumber.parse(command.phone), self._clock.now()
        with self._uow_factory() as uow:
            user, temporary = uow.users.find_by_phone(phone), None
            if user is None:
                temporary = draw_temporary_pin(self._pins, phone)
                user = User.register(
                    phone=phone, name=command.name, secret_hash=self._hasher.hash(temporary)
                )
                uow.users.add(user)
            elif user.is_platform_admin:
                msg = "Ce numéro est celui de l'administrateur plateforme"
                raise ValidationFailed(msg, details={"field": "phone"})
            with uow.join_shop(actor_shop(actor)) as shop_uow:
                profile = profile_for(ShopRepository.within(shop_uow).current().profile_code)
                membership = Membership.add(
                    shop_id=shop_uow.shop_id,
                    user_id=user.id,
                    role=command.role,
                    location=_location(shop_uow, command.default_location_id),
                    profile=profile,
                    performer=performer_of(actor),
                    now=now,
                )
                MembershipRepository.within(shop_uow).add(membership)
                shop_uow.commit()
            uow.commit()
        return AddedMember(member=member_view(membership, user, now), temporary_pin=temporary)

    def update(self, actor: Actor, target: UserId, command: UpdateMemberCommand) -> MemberView:
        self._policy.require(actor, Permission.MEMBER_MANAGE)
        performer, now = performer_of(actor), self._clock.now()
        with self._uow_factory() as uow:
            with uow.join_shop(actor_shop(actor)) as shop_uow:
                memberships = MembershipRepository.within(shop_uow)
                membership = memberships.find_by_user(target)
                if membership is None:
                    raise not_found(target)
                require_version(membership.version, command.version)
                was_owner, changed = membership.is_active_owner, False
                if command.role is not None or command.location_given:
                    role = command.role or membership.role
                    kept = membership.default_location_id if role is Role.SELLER else None
                    wanted = command.default_location_id if command.location_given else kept
                    profile = profile_for(ShopRepository.within(shop_uow).current().profile_code)
                    changed = membership.assign(
                        role,
                        _location(shop_uow, wanted),
                        profile=profile,
                        performer=performer,
                        now=now,
                    )
                if command.active is not None and command.active is not membership.active:
                    membership.set_active(command.active, performer=performer, now=now)
                    changed = True
                if was_owner and not membership.is_active_owner:
                    self._keep_an_owner(shop_uow, membership)
                if changed:
                    memberships.update(membership)
                    shop_uow.commit()
            user = uow.users.get(target)
            if changed:
                uow.commit()
        return member_view(membership, user, now)

    @staticmethod
    def _keep_an_owner(uow: UnitOfWork, leaving: Membership) -> None:
        """RG-D08 : un autre propriétaire actif doit rester ; garde contre la concurrence."""
        others = MembershipRepository.within(uow).list_all()
        if not any(m.is_active_owner for m in others if m.id != leaving.id):
            raise LastActiveOwner
        shops = ShopRepository.within(uow)
        shops.update(shops.current())
