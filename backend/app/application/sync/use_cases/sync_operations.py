"""UC-VEN-10 (et dépense hors connexion) — `POST /sync` : rejouer la file de l'appareil (§ 6.5).

1. Accès à la boutique d'abord (`Policy`, specs § 8.3) : l'administrateur sans délégation
   reçoit 404 comme un non-membre, jamais l'état des droits d'offre de la boutique (T24).
   Puis droit `offline_capture` exigé (`require_entitlement` → 403 `FEATURE_DISABLED`,
   TR-26) : en V1, faux pour toute boutique ; seule une surcharge de l'administrateur l'ouvre.
2. `device_id` du lot = appareil de la session (sinon 400) ; au plus `MAX_OPERATIONS`.
3. Opérations traitées **dans l'ordre**, chacune dans sa propre transaction (RG-T23) :
   - `op_id` déjà connu → résultat gardé : `duplicate` (+ numéro définitif) ou de nouveau
     `rejected` avec le même motif ; rien n'est rejoué (idempotence, TR-11, OFF-05) ;
   - sinon exécution (`OperationRunner`) ; une **erreur métier** (`DomainError`) rend
     l'opération `rejected` — elle n'est pas avalée : elle est gardée (`sync_operation`),
     journalisée et alertée (« Saisie refusée », OFF-07) et renvoyée avec son code ; les
     suivantes continuent. Toute autre exception remonte (500, fail-fast) : les opérations
     déjà validées le restent, le client renverra le lot et les recevra en `duplicate`.
4. Trace écrite **après** le document, dans une transaction courte : si elle échoue, le
   prochain envoi retrouve le document par son identifiant (= `op_id`) → `duplicate`.
"""

from app.application.plans.entitlements import require_entitlement
from app.application.plans.ports import Entitlements
from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWorkFactory
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop, performer_of
from app.application.sync.inputs import (
    MAX_OPERATIONS,
    OperationDecoder,
    OperationInput,
    OperationNotice,
    OperationResult,
    Outcome,
    ResultStatus,
    SyncBatch,
)
from app.application.sync.ports import SyncOperationRepository
from app.application.sync.runner import OperationRunner
from app.domain.plans.entitlements import Entitlement
from app.domain.shared.errors import DomainError, Duplicate, ValidationFailed
from app.domain.sync.errors import OperationIdConflict
from app.domain.sync.operation import SyncOperation, SyncOrigin, SyncStatus


def replayed(known: SyncOperation) -> OperationResult:
    """Résultat d'un `op_id` déjà traité, sans rien réexécuter."""
    if known.status is SyncStatus.ACCEPTED:
        return OperationResult(
            op_id=known.id,
            status=ResultStatus.DUPLICATE,
            provisional_number=known.provisional_number,
            number=known.number,
            entity_id=known.entity_id,
        )
    return OperationResult(
        op_id=known.id,
        status=ResultStatus.REJECTED,
        provisional_number=known.provisional_number,
        error=OperationNotice(str(known.error_code), str(known.error_message)),
    )


class SyncOperations:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        entitlements: Entitlements,
        runner: OperationRunner,
        clock: Clock,
        policy: Policy,
    ) -> None:
        self._policy = policy
        self._uow_factory = uow_factory
        self._entitlements = entitlements
        self._runner = runner
        self._clock = clock

    def execute(
        self, actor: Actor, batch: SyncBatch, decoder: OperationDecoder
    ) -> list[OperationResult]:
        self._policy.require(actor, Permission.HOME_READ)  # 404 hors boutique, avant tout
        require_entitlement(self._entitlements, actor_shop(actor), Entitlement.OFFLINE_CAPTURE)
        if batch.device_id != actor.device_id:
            msg = "device_id du lot différent de l'appareil de la session"
            raise ValidationFailed(msg, details={"field": "device_id"})
        if len(batch.operations) > MAX_OPERATIONS:
            msg = f"Au plus {MAX_OPERATIONS} opérations par envoi"
            raise ValidationFailed(msg, details={"field": "operations", "max": MAX_OPERATIONS})
        return [self._one(actor, operation, decoder) for operation in batch.operations]

    def _one(
        self, actor: Actor, operation: OperationInput, decoder: OperationDecoder
    ) -> OperationResult:
        known = self._find(actor, operation)
        if known is not None:
            return self._replay(actor, operation, known)
        try:
            outcome = self._runner.run(actor, operation, decoder)
        except DomainError as error:  # refus métier : gardé, journalisé, alerté, renvoyé
            return self._reject(actor, operation, error)
        return self._accept(actor, operation, outcome)

    def _find(self, actor: Actor, operation: OperationInput) -> SyncOperation | None:
        with self._uow_factory(actor_shop(actor)) as uow:
            return SyncOperationRepository.within(uow).find(operation.op_id)

    def _replay(
        self, actor: Actor, operation: OperationInput, known: SyncOperation
    ) -> OperationResult:
        if known.origin.created_by != actor.user_id:
            msg = "Identifiant d'opération déjà utilisé par un autre utilisateur"
            error = OperationIdConflict(msg)
            return OperationResult(
                op_id=operation.op_id,
                status=ResultStatus.REJECTED,
                provisional_number=operation.provisional_number,
                error=OperationNotice(error.code, error.message),
            )
        return replayed(known)

    def _origin(self, actor: Actor, operation: OperationInput) -> SyncOrigin:
        return SyncOrigin(
            created_by=actor.user_id,
            device_id=actor.device_id,
            captured_at=operation.captured_at,
            received_at=self._clock.now(),
        )

    def _accept(self, actor: Actor, operation: OperationInput, outcome: Outcome) -> OperationResult:
        trace = SyncOperation.accepted(
            operation.op_id,
            actor_shop(actor),
            op_type=operation.type,
            origin=self._origin(actor, operation),
            provisional_number=operation.provisional_number,
            entity_id=outcome.entity_id,
            number=outcome.number,
        )
        if not self._store(actor, trace):
            return self._replay(actor, operation, self._require(actor, operation))
        return OperationResult(
            op_id=operation.op_id,
            status=ResultStatus.ACCEPTED if outcome.created else ResultStatus.DUPLICATE,
            provisional_number=operation.provisional_number,
            number=outcome.number,
            entity_id=outcome.entity_id,
            warnings=outcome.warnings,
        )

    def _reject(
        self, actor: Actor, operation: OperationInput, error: DomainError
    ) -> OperationResult:
        trace = SyncOperation.rejected(
            operation.op_id,
            actor_shop(actor),
            op_type=operation.type,
            origin=self._origin(actor, operation),
            provisional_number=operation.provisional_number,
            error_code=error.code,
            error_message=error.message,
            performer=performer_of(actor),
        )
        if not self._store(actor, trace):
            return self._replay(actor, operation, self._require(actor, operation))
        return OperationResult(
            op_id=operation.op_id,
            status=ResultStatus.REJECTED,
            provisional_number=operation.provisional_number,
            error=OperationNotice(error.code, error.message, error.details),
        )

    def _store(self, actor: Actor, trace: SyncOperation) -> bool:
        """Écrit la trace ; `False` si un envoi concurrent du même `op_id` l'a écrite avant."""
        try:
            with self._uow_factory(actor_shop(actor)) as uow:
                SyncOperationRepository.within(uow).add(trace)
                uow.commit()
        except Duplicate:  # course connue : la trace concurrente fait foi (relue par l'appelant)
            return False
        return True

    def _require(self, actor: Actor, operation: OperationInput) -> SyncOperation:
        known = self._find(actor, operation)
        if known is None:
            msg = f"Trace de synchronisation {operation.op_id} introuvable après un doublon"
            raise RuntimeError(msg)
        return known
