"""Droits sur une pièce jointe : ils **héritent** de l'élément lié (CDC § 20.5, § 4.2).

| Élément lié | Envoyer | Voir | « Siens » du vendeur |
| --- | --- | --- | --- |
| client | `CUSTOMER_MANAGE` | `CUSTOMER_READ` | client créé par lui ou une vente de lui (Q-20) |
| créance, garants | `RECEIVABLE_FOLLOW_UP` | `RECEIVABLE_READ` | vendeur responsable (Q-21) |
| article | `ARTICLE_WRITE` | `STOCK_READ` | — |
| dépense | `EXPENSE_CREATE` | `EXPENSE_READ` | — |
| achat | `PURCHASE_WRITE` | `PURCHASE_READ` | — |
| ajustement de stock | `STOCK_ADJUST` | `STOCK_HISTORY_READ` | — |

Permission absente → 403 (journalisé). Élément hors de la portée de l'acteur ou d'une autre
boutique → 404 (aucune fuite d'existence). **Pièce d'identité** (UC-CRE-07, SEC-N06) : le
propriétaire et le vendeur dans la portée seulement ; tout autre acteur, l'administrateur
délégué compris, reçoit 403.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from uuid import UUID

from app.application.ports.repository import not_found
from app.application.ports.uow import UnitOfWork
from app.application.receivables.ports import ReceivableRepository
from app.application.sales.ports import CustomerRepository
from app.application.security.access import OwnScope
from app.application.security.actor import Actor
from app.application.security.errors import PermissionDenied
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.security.roles import Role
from app.domain.attachments.attachment import Attachment
from app.domain.attachments.values import OwnerType
from app.domain.receivables.ids import ReceivableId
from app.domain.sales.ids import CustomerId
from app.domain.shared.ids import UserId

P = Permission


@dataclass(frozen=True, slots=True)
class OwnerRights:
    write: Permission
    read: Permission


RIGHTS: Mapping[OwnerType, OwnerRights] = MappingProxyType(
    {
        OwnerType.CUSTOMER: OwnerRights(P.CUSTOMER_MANAGE, P.CUSTOMER_READ),
        OwnerType.RECEIVABLE: OwnerRights(P.RECEIVABLE_FOLLOW_UP, P.RECEIVABLE_READ),
        OwnerType.ARTICLE: OwnerRights(P.ARTICLE_WRITE, P.STOCK_READ),
        OwnerType.EXPENSE: OwnerRights(P.EXPENSE_CREATE, P.EXPENSE_READ),
        OwnerType.PURCHASE: OwnerRights(P.PURCHASE_WRITE, P.PURCHASE_READ),
        OwnerType.STOCK_ADJUSTMENT: OwnerRights(P.STOCK_ADJUST, P.STOCK_HISTORY_READ),
    }
)
if set(RIGHTS) != set(OwnerType):  # tout nouvel élément lié doit déclarer ses droits
    _msg = f"Droits des pièces jointes non déclarés pour {sorted(set(OwnerType) - set(RIGHTS))}"
    raise RuntimeError(_msg)


class AttachmentAccess:
    def __init__(self, policy: Policy) -> None:
        self._policy = policy

    def require_upload(
        self, uow: UnitOfWork, actor: Actor, owner_type: OwnerType, owner_id: UUID | None
    ) -> None:
        """Droit d'envoi, puis élément lié visible (client, créance) ; 403 puis 404."""
        permission = RIGHTS[owner_type].write
        self._policy.require(actor, permission)
        if owner_type.is_personal:
            self._require_owner_visible(uow, actor, owner_type, owner_id, permission)

    def require_read(self, uow: UnitOfWork, actor: Actor, attachment: Attachment) -> None:
        """Droit de lecture de l'élément lié, portée « Siens », pièce d'identité réservée."""
        file = attachment.file
        permission = RIGHTS[file.owner_type].read
        self._policy.require(actor, permission)
        if file.owner_type.is_personal:
            self._require_owner_visible(uow, actor, file.owner_type, file.owner_id, permission)
        if attachment.is_id_document and actor.role not in (Role.OWNER, Role.SELLER):
            raise PermissionDenied(actor, permission)

    def _require_owner_visible(
        self,
        uow: UnitOfWork,
        actor: Actor,
        owner_type: OwnerType,
        owner_id: UUID | None,
        permission: Permission,
    ) -> None:
        if owner_id is None:  # exclu par `AttachmentFile` : défense en profondeur
            msg = "Pièce jointe personnelle sans élément lié"
            raise RuntimeError(msg)
        scope = self._policy.scope_filter(actor, permission)
        seller = scope.user_id if isinstance(scope, OwnScope) else None
        if owner_type is OwnerType.CUSTOMER:
            _require_customer(uow, CustomerId(owner_id), seller)
        elif owner_type is OwnerType.RECEIVABLE:
            _require_receivable(uow, ReceivableId(owner_id), seller)
        else:
            msg = f"Élément personnel sans règle de portée : {owner_type}"
            raise RuntimeError(msg)


def _require_customer(uow: UnitOfWork, customer_id: CustomerId, seller: UserId | None) -> None:
    customers = CustomerRepository.within(uow)
    found = customers.find(customer_id)
    if found is None or (seller is not None and not customers.visible_to(customer_id, seller)):
        raise not_found(customer_id)


def _require_receivable(
    uow: UnitOfWork, receivable_id: ReceivableId, seller: UserId | None
) -> None:
    found = ReceivableRepository.within(uow).find(receivable_id)
    if found is None or (seller is not None and found.responsible_seller_id != seller):
        raise not_found(receivable_id)
