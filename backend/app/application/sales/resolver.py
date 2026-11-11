"""Saisie d'une vente → éléments vérifiés dans la transaction (UC-VEN-01, UC-VEN-02).

- **Lieu (Q-36 tranchée)** : le vendeur vend depuis **son lieu de vente habituel** (celui de
  son rattachement) ; un autre lieu → `LOCATION_NOT_ALLOWED`. Le propriétaire choisit tout
  point de vente actif ; s'il n'en donne pas et qu'il n'y en a qu'un, celui-ci est retenu. Un
  lieu qui n'est pas un point de vente actif → `LOCATION_NOT_POINT_OF_SALE` (SAL-03).
- **Vendeur** : l'auteur ; le propriétaire peut attribuer la vente à un membre actif
  vendeur ou propriétaire (CDC § 20.4) ; un vendeur ne peut attribuer qu'à lui-même (403).
- **Client** : existant par `id` (pour un vendeur : un de « ses clients », sinon 404) ; sinon
  création rapide nom + téléphone + type. Un téléphone déjà connu de la boutique **réutilise**
  la fiche existante (fusion par téléphone, UC-VEN-10 ; Q-20 tranchée : le vendeur peut alors
  vendre à ce client, qui devient « un de ses clients » par cette vente).
- **Paiements** : mode actif de la boutique, montant > 0, référence facultative.
"""

from datetime import datetime

from app.application.ports.repository import not_found
from app.application.ports.uow import UnitOfWork
from app.application.sales.inputs import CustomerInput, PaymentInput
from app.application.sales.ports import CustomerRepository
from app.application.security.actor import Actor
from app.application.security.errors import PermissionDenied
from app.application.security.permissions import Permission
from app.application.security.roles import Role
from app.application.shops.context import performer_of
from app.application.shops.ports import (
    LocationRepository,
    MembershipRepository,
    PaymentModeRepository,
)
from app.domain.identity.phone import PhoneNumber
from app.domain.sales.customer import Customer, CustomerDetails
from app.domain.sales.errors import LocationNotAllowed
from app.domain.sales.ids import CustomerId, SalePaymentId
from app.domain.sales.payments import SalePayment
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.ids import UserId
from app.domain.shared.money import Money
from app.domain.shops.errors import NotPointOfSale
from app.domain.shops.ids import LocationId

SELLING_ROLES = frozenset({Role.SELLER, Role.OWNER})


def sale_location(uow: UnitOfWork, actor: Actor, wanted: LocationId | None) -> LocationId:
    locations = LocationRepository.within(uow)
    if actor.role is not Role.OWNER:
        membership = MembershipRepository.within(uow).find_by_user(actor.user_id)
        usual = None if membership is None else membership.default_location_id
        if usual is None or (wanted is not None and wanted != usual):
            raise LocationNotAllowed(str(wanted), None if usual is None else str(usual))
        wanted = usual
    if wanted is None:
        points = [loc for loc in locations.list_all() if loc.is_active_point_of_sale]
        if len(points) != 1:
            msg = "Lieu de vente obligatoire : choisissez un point de vente"
            raise ValidationFailed(msg, details={"field": "location_id"})
        return points[0].id
    location = locations.get(wanted)
    if not location.is_active_point_of_sale:
        raise NotPointOfSale(str(location.id))
    return location.id


def sale_seller(uow: UnitOfWork, actor: Actor, wanted: UserId | None) -> UserId:
    if wanted is None or wanted == actor.user_id:
        return actor.user_id
    if actor.role is not Role.OWNER:
        raise PermissionDenied(actor, Permission.SALE_CREATE)
    membership = MembershipRepository.within(uow).find_by_user(wanted)
    if membership is None or not membership.active or membership.role not in SELLING_ROLES:
        msg = "Vendeur inconnu ou inactif dans cette boutique"
        raise ValidationFailed(msg, details={"field": "seller_id"})
    return wanted


def require_visible(uow: UnitOfWork, actor: Actor, customer_id: CustomerId) -> Customer:
    """Client lisible par l'acteur : tous pour le propriétaire, « ses clients » pour le vendeur."""
    customers = CustomerRepository.within(uow)
    customer = customers.get(customer_id)
    if actor.role is not Role.OWNER and not customers.visible_to(customer.id, actor.user_id):
        raise not_found(customer_id)
    return customer


def sale_customer(
    uow: UnitOfWork, actor: Actor, wanted: CustomerInput | None, now: datetime
) -> Customer | None:
    if wanted is None:
        return None
    if wanted.customer_id is not None:
        return require_visible(uow, actor, wanted.customer_id)
    if wanted.phone is None or wanted.name is None:
        msg = "Nom et téléphone du client obligatoires"
        raise ValidationFailed(msg, details={"field": "customer"})
    customers = CustomerRepository.within(uow)
    phone = PhoneNumber.parse(wanted.phone)
    existing = customers.find_by_phone(phone)
    if existing is not None:
        return existing
    details = CustomerDetails(name=wanted.name, phone=phone, kind=wanted.kind)
    customer = Customer.create(uow.shop_id, details, performer=performer_of(actor), now=now)
    customers.add(customer)
    return customer


def sale_payments(uow: UnitOfWork, payments: tuple[PaymentInput, ...]) -> tuple[SalePayment, ...]:
    modes = PaymentModeRepository.within(uow)
    resolved = []
    for item in payments:
        mode = modes.get(item.mode_id)
        if not mode.details.active:
            msg = "Mode de paiement désactivé : choisissez-en un autre"
            raise ValidationFailed(msg, details={"field": "payments.mode_id"})
        resolved.append(
            SalePayment(
                id=item.payment_id or SalePaymentId.new(),
                mode_id=mode.id,
                amount=Money.entry(item.amount, "payments.amount"),
                reference=item.reference,
            )
        )
    return tuple(resolved)
