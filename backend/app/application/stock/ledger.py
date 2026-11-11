"""`StockLedger` : **seul** point d'entrée pour enregistrer un mouvement (TR-12, TR-13, H21).

API pour les modules métier, à appeler **dans leur unité de travail** (même transaction que le
document source ; le `commit` reste à l'appelant) :

- `record_entry(uow, posting)` : type d'entrée (Entrée achat, Retour client, Ajustement +,
  Reprise de départ, Arrivée de déplacement) ; jamais refusée pour cause de stock.
- `record_exit(uow, posting, deferred=False)` : type de sortie (Sortie vente, Ajustement -,
  Chute, Départ ou Manquant de déplacement). **En ligne** (RG-T17), refus si le solde du lieu
  dans cet état passerait sous zéro : `StockInsufficient` (`available`, `other_locations`).
  **Différé** (RG-T18, saisie hors ligne rejouée) : acceptée, mouvement `stock_to_verify`,
  alerte « Stock à vérifier » au propriétaire et au comptable.
- `reverse(uow, movement_id, source=…, author_id=…, occurred_at=…)` : « Annulation », quantité
  opposée au mouvement visé (une seule fois : `MovementAlreadyReversed`) ; une annulation qui
  retire du stock suit la règle en ligne (une entrée déjà vendue ne s'annule pas).

Chaque mouvement met à jour la projection `StockLevel` (verrou optimiste) et émet
`StockTotalChanged` (stock bas) ; deux sorties simultanées : la seconde échoue au `commit`
(`VersionConflict`) — rejouer la transaction par `with_stock_retry` (`retry.py`).
"""

from datetime import datetime
from decimal import Decimal

from app.application.catalog.ports import ArticleRepository
from app.application.ports.clock import Clock
from app.application.ports.repository import not_found
from app.application.ports.uow import UnitOfWork
from app.application.shops.ports import LocationRepository, ShopSettingsRepository
from app.application.stock.availability import other_locations, sellable_total
from app.application.stock.ports import StockLevelRepository, StockMovementLog
from app.application.stock.postings import Posting, SignedPosting
from app.domain.catalog.article import Article
from app.domain.shared.errors import InvalidStateTransition, ValidationFailed
from app.domain.shared.ids import UserId
from app.domain.shared.quantity import Quantity
from app.domain.shops.location import Location
from app.domain.stock.errors import MovementAlreadyReversed, StockInsufficient
from app.domain.stock.events import StockBecameNegative, StockTotalChanged
from app.domain.stock.ids import StockMovementId
from app.domain.stock.level import StockLevel
from app.domain.stock.movement import StockMovement
from app.domain.stock.values import ENTRY_TYPES, EXIT_TYPES, MovementType, SourceRef, StockCondition


class StockLedger:
    def __init__(self, clock: Clock) -> None:
        self._clock = clock

    # ------------------------------------------------------------------ API publique
    def record_entry(self, uow: UnitOfWork, posting: Posting) -> StockMovement:
        if posting.type not in ENTRY_TYPES:
            msg = f"record_entry attend un type d'entrée, reçu {posting.type.value}"
            raise ValueError(msg)
        return self._post(uow, SignedPosting(posting=posting, signed=posting.quantity))

    def record_exit(
        self, uow: UnitOfWork, posting: Posting, *, deferred: bool = False
    ) -> StockMovement:
        if posting.type not in EXIT_TYPES:
            msg = f"record_exit attend un type de sortie, reçu {posting.type.value}"
            raise ValueError(msg)
        signed = SignedPosting(posting=posting, signed=-posting.quantity, deferred=deferred)
        return self._post(uow, signed)

    def reverse(
        self,
        uow: UnitOfWork,
        movement_id: StockMovementId,
        *,
        source: SourceRef,
        author_id: UserId,
        occurred_at: datetime,
    ) -> StockMovement:
        log = StockMovementLog.within(uow)
        original = log.find(movement_id)
        if original is None:
            raise not_found(movement_id)
        if original.type is MovementType.REVERSAL:
            msg = "Une annulation ne s'annule pas"
            raise InvalidStateTransition(msg, details={"movement_id": str(movement_id)})
        if log.reversal_of(movement_id) is not None:
            raise MovementAlreadyReversed(str(movement_id))
        posting = Posting(
            article_id=original.article_id,
            location_id=original.location_id,
            type=MovementType.REVERSAL,
            quantity=abs_quantity(original),
            source=source,
            occurred_at=occurred_at,
            author_id=author_id,
            condition=original.condition,
            unit_cost=original.unit_cost,
        )
        signed = SignedPosting(posting=posting, signed=-original.quantity, reverses=original.id)
        return self._post(uow, signed)

    # ------------------------------------------------------------------ interne
    def _post(self, uow: UnitOfWork, request: SignedPosting) -> StockMovement:
        posting = request.posting
        article = ArticleRepository.within(uow).get(posting.article_id)
        location = LocationRepository.within(uow).get(posting.location_id)
        if not location.active:
            msg = "Ce lieu est désactivé"
            raise ValidationFailed(msg, details={"field": "location_id"})
        if posting.quantity.unit is not article.details.fields.stock_unit:
            msg = "Quantité dans une autre unité que l'unité de stock de l'article"
            raise ValueError(msg)
        levels = StockLevelRepository.within(uow)
        all_levels = levels.for_article(article.id)
        before = sellable_total(all_levels)
        level = levels.find_level(article.id, location.id) or StockLevel.empty(
            uow.shop_id, article.id, location.id, posting.quantity.unit
        )
        condition, signed = posting.condition, request.signed
        current = level.balance(condition)
        if signed.value < 0 and (current + signed).value < 0 and not request.deferred:
            raise StockInsufficient(
                article_id=str(article.id),
                location_id=str(location.id),
                available=current,
                requested=-signed,
                other_locations=other_locations(uow, all_levels, location.id, condition),
            )
        balance = level.apply(signed, condition)
        movement = StockMovement(
            id=StockMovementId.new(),
            shop_id=uow.shop_id,
            article_id=article.id,
            location_id=location.id,
            type=posting.type,
            condition=condition,
            quantity=signed,
            balance_after=balance,
            source=posting.source,
            occurred_at=posting.occurred_at,
            recorded_at=self._clock.now(),
            author_id=posting.author_id,
            unit_cost=posting.unit_cost,
            stock_to_verify=balance.value < 0,
            reverses=request.reverses,
        )
        StockMovementLog.within(uow).append(movement)
        self._record_events(uow, level, article, location, movement, before)
        if level.version == 0:
            levels.add(level)
        else:
            levels.update(level)
        return movement

    def _record_events(
        self,
        uow: UnitOfWork,
        level: StockLevel,
        article: Article,
        location: Location,
        movement: StockMovement,
        before: Decimal,
    ) -> None:
        now = self._clock.now()
        if movement.condition is StockCondition.SELLABLE:
            shop_default = ShopSettingsRepository.within(uow).current().values.low_stock_threshold
            level.events.record(
                StockTotalChanged(
                    shop_id=uow.shop_id,
                    occurred_at=now,
                    article_id=article.id,
                    article_name=article.display_name,
                    before=before,
                    after=before + movement.quantity.value,
                    threshold=article.details.effective_threshold(shop_default),
                )
            )
        if movement.stock_to_verify:
            level.events.record(
                StockBecameNegative(
                    shop_id=uow.shop_id,
                    occurred_at=now,
                    article_id=article.id,
                    article_name=article.display_name,
                    location_id=location.id,
                    location_name=location.name,
                    balance=movement.balance_after.value,
                )
            )


def abs_quantity(movement: StockMovement) -> Quantity:
    quantity = movement.quantity
    return -quantity if quantity.value < 0 else quantity
