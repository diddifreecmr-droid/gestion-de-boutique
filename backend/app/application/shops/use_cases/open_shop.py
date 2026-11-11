"""UC-SOC-01 — Ouvrir l'espace d'une boutique (administrateur plateforme ; recette PLT-01 à 04).

Dans **une seule transaction** (unité plateforme + boutique jointe, voir `identity/uow.py`) :

1. le compte commerçant est retrouvé par le téléphone du propriétaire, ou créé (offre gratuite
   permanente) ; le nom de la boutique doit y être libre (`Duplicate`) ;
2. le propriétaire : si un compte porte déjà ce téléphone, il est **rattaché** à la nouvelle
   boutique, sans doublon ni nouveau code (son code reste le sien, recette Q-27) ; sinon il est
   créé avec un code provisoire, renvoyé **une seule fois** (`must_change_pin = true`). Le
   téléphone de l'administrateur plateforme est refusé (il n'a pas de rôle de boutique) ;
3. la boutique, ses lieux, réglages, modes de paiement, catégories et le rattachement
   « Propriétaire » sont créés selon le profil (`seeding.py`).
"""

from dataclasses import dataclass

from app.application.identity.ports import PasswordHasher, TemporaryPinGenerator
from app.application.identity.temporary_pins import draw_temporary_pin
from app.application.identity.uow import IdentityUnitOfWork, IdentityUnitOfWorkFactory
from app.application.ports.clock import Clock
from app.application.security.actor import Actor
from app.application.security.policy import Policy
from app.application.shops.context import performer_of
from app.application.shops.seeding import SeedRequest, seed_shop
from app.domain.identity.phone import PhoneNumber
from app.domain.identity.user import User
from app.domain.profiles.registry import profile_for
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.ids import ShopId, UserId
from app.domain.shops.account import MerchantAccount
from app.domain.shops.ids import MerchantAccountId
from app.domain.shops.shop import Shop, ShopIdentity


@dataclass(frozen=True, slots=True, kw_only=True)
class OpenShopCommand:
    profile_code: str
    name: str
    city: str
    phone: str
    owner_name: str
    owner_phone: str
    address: str | None = None
    niu: str | None = None
    rccm: str | None = None
    account_name: str | None = None
    """Nom du compte commerçant s'il est créé (défaut : nom du propriétaire)."""


@dataclass(frozen=True, slots=True, kw_only=True)
class OpenedShop:
    shop_id: ShopId
    account_id: MerchantAccountId
    owner_id: UserId
    owner_created: bool
    temporary_pin: str | None
    """Code provisoire du propriétaire créé, à transmettre ; `None` s'il existait déjà."""


def _phone(text: str, field: str) -> PhoneNumber:
    try:
        return PhoneNumber.parse(text)
    except ValidationFailed as exc:
        msg = "Numéro de téléphone invalide"
        raise ValidationFailed(msg, details={"field": field}) from exc


class OpenShop:
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

    def execute(self, actor: Actor, command: OpenShopCommand) -> OpenedShop:
        self._policy.require_platform_admin(actor)
        profile = profile_for(command.profile_code)
        identity = ShopIdentity(
            name=command.name,
            city=command.city,
            phone=_phone(command.phone, "phone"),
            address=command.address,
            niu=command.niu,
            rccm=command.rccm,
        )
        owner_phone = _phone(command.owner_phone, "owner_phone")
        now, shop_id = self._clock.now(), ShopId.new()
        with self._uow_factory() as uow:
            account = uow.merchants.find_by_phone(owner_phone)
            if account is None:
                account = MerchantAccount.create(
                    name=command.account_name or command.owner_name, phone=owner_phone
                )
            account.register_shop(shop_id, identity.name)
            save = uow.merchants.update if account.version else uow.merchants.add
            save(account)
            owner, temporary = self._owner(uow, command.owner_name, owner_phone)
            shop = Shop.open(
                shop_id=shop_id,
                account_id=account.id,
                profile_code=profile.code,
                identity=identity,
                modules=profile.modules,
                performer=performer_of(actor),
                now=now,
            )
            with uow.join_shop(shop_id) as shop_uow:
                request = SeedRequest(
                    shop=shop,
                    profile=profile,
                    owner_id=owner.id,
                    performer=performer_of(actor),
                    now=now,
                )
                seed_shop(shop_uow, request)
                shop_uow.commit()
            uow.commit()
        return OpenedShop(
            shop_id=shop_id,
            account_id=account.id,
            owner_id=owner.id,
            owner_created=temporary is not None,
            temporary_pin=temporary,
        )

    def _owner(
        self, uow: IdentityUnitOfWork, name: str, phone: PhoneNumber
    ) -> tuple[User, str | None]:
        existing = uow.users.find_by_phone(phone)
        if existing is not None:
            if existing.is_platform_admin:
                msg = "Ce numéro est celui de l'administrateur plateforme"
                raise ValidationFailed(msg, details={"field": "owner_phone"})
            return existing, None
        temporary = draw_temporary_pin(self._pins, phone)
        user = User.register(phone=phone, name=name, secret_hash=self._hasher.hash(temporary))
        uow.users.add(user)
        return user, temporary
