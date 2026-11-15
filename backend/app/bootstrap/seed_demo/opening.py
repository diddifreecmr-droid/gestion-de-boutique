"""Ouverture d'une boutique de démonstration : boutique, gérant, employés, comptable.

Tout passe par `OpenShop` (comme l'administrateur plateforme) puis `ManageMembers` (comme le
gérant) ; chaque compte reçoit son code provisoire **connu** (`KnownPins`) et garde
`must_change_pin` : il devra le changer à la première connexion.
"""

from dataclasses import dataclass

from app.application.security.actor import Actor
from app.application.shops.ports import LocationRepository
from app.application.shops.use_cases.manage_members import AddMemberCommand
from app.application.shops.use_cases.open_shop import OpenShopCommand
from app.bootstrap.seed_demo.plan import Person, ShopPlan
from app.bootstrap.seed_demo.services import DemoServices
from app.domain.shared.ids import DeviceId, ShopId, UserId
from app.domain.shared.roles import Role
from app.domain.shops.ids import LocationId

EXISTING = "(compte existant)"
"""Affiché à la place du code quand le numéro était déjà inscrit (code inchangé)."""


@dataclass(frozen=True, slots=True, kw_only=True)
class OpenedDemo:
    shop_id: ShopId
    owner: Actor
    sellers: tuple[Actor, Actor]
    accountant: Actor
    store_id: LocationId
    codes: dict[str, str]
    """Téléphone → code provisoire remis (ou `EXISTING`)."""


def _member(user_id: UserId, shop_id: ShopId, role: Role) -> Actor:
    return Actor.member(user_id=user_id, device_id=DeviceId.new(), shop_id=shop_id, role=role)


def _point_of_sale(services: DemoServices, shop_id: ShopId) -> LocationId:
    with services.identity.core.shop_uow_factory(shop_id) as uow:
        places = [loc for loc in LocationRepository.within(uow).list_all() if loc.details.active]
    for place in places:
        if place.details.is_point_of_sale:
            return place.id
    msg = f"Boutique {shop_id} sans point de vente actif"
    raise RuntimeError(msg)


def open_demo_shop(services: DemoServices, admin: Actor, plan: ShopPlan) -> OpenedDemo:
    command = OpenShopCommand(
        profile_code=plan.profile.value,
        name=plan.name,
        city=plan.city,
        phone=plan.phone,
        owner_name=plan.owner.name,
        owner_phone=plan.owner.phone,
    )
    services.pins.expect(plan.owner.pin)
    opened = services.shops.open_shop.execute(admin, command)
    codes = {plan.owner.phone: opened.temporary_pin or EXISTING}
    owner = _member(opened.owner_id, opened.shop_id, Role.OWNER)
    store = _point_of_sale(services, opened.shop_id)
    members = [_add(services, owner, person, store, codes) for person in plan.people[1:]]
    sellers = (
        _member(members[0], opened.shop_id, Role.SELLER),
        _member(members[1], opened.shop_id, Role.SELLER),
    )
    return OpenedDemo(
        shop_id=opened.shop_id,
        owner=owner,
        sellers=sellers,
        accountant=_member(members[2], opened.shop_id, Role.ACCOUNTANT),
        store_id=store,
        codes=codes,
    )


def _add(
    services: DemoServices, owner: Actor, person: Person, store: LocationId, codes: dict[str, str]
) -> UserId:
    services.pins.expect(person.pin)
    location = store if person.role is Role.SELLER else None
    added = services.shops.members.add(
        owner,
        AddMemberCommand(
            name=person.name, phone=person.phone, role=person.role, default_location_id=location
        ),
    )
    codes[person.phone] = added.temporary_pin or EXISTING
    return added.member.membership.user_id
