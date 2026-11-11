"""Coûts des articles tirés du grand livre : rejeu du CMP et du dernier coût (TR-14, Q-02).

`refresh_costs` est appelé dans la transaction de chaque achat, correction ou annulation, après
les mouvements : pour chaque article touché, il relit **tous** ses mouvements (tous lieux,
`StockMovementLog.chronology`), retire les paires « mouvement annulé + Annulation » (l'achat
corrigé est rejoué « comme s'il avait été saisi juste dès le départ », UC-ACH-03), rejoue le
CMP sur le stock réel (`replay_wac`) puis écrit `last_cost` et `wac` par `Article.record_costs`.

Les ventes passées ne bougent pas : leurs coûts sont **figés dans la vente** (RG-T13, T16) ;
seuls les coûts courants de l'article changent. Un article dont il ne reste aucune entrée
coûtée revient à « coût inconnu » (`None`, RG-T15).
"""

from collections.abc import Iterable, Sequence
from uuid import UUID

from app.application.catalog.ports import ArticleRepository
from app.application.ports.uow import UnitOfWork
from app.application.stock.ports import StockMovementLog
from app.domain.catalog.ids import ArticleId
from app.domain.purchasing.replay import CostEvent, CostState, replay_wac
from app.domain.stock.movement import StockMovement
from app.domain.stock.values import COSTED_ENTRIES


def cost_events(
    movements: Sequence[StockMovement], *, exclude_source: UUID | None = None
) -> list[CostEvent]:
    """Mouvements vus par le Costing : sans les paires annulées ni le document `exclude_source`."""
    reversed_ids = {m.reverses for m in movements if m.reverses is not None}
    events = []
    for movement in movements:
        if movement.reverses is not None or movement.id in reversed_ids:
            continue  # paire « mouvement + Annulation » : comme si elle n'avait jamais existé
        if exclude_source is not None and movement.source.id == exclude_source:
            continue
        costed = movement.type in COSTED_ENTRIES
        events.append(
            CostEvent(
                at=movement.occurred_at,
                order=movement.id.value,
                quantity=movement.quantity.value,
                unit_cost=movement.unit_cost if costed else None,
                sets_cost=costed,
            )
        )
    return events


def replay_article(
    uow: UnitOfWork, article_id: ArticleId, *, exclude_source: UUID | None = None
) -> CostState:
    movements = StockMovementLog.within(uow).chronology(article_id)
    return replay_wac(cost_events(movements, exclude_source=exclude_source))


def refresh_costs(uow: UnitOfWork, article_ids: Iterable[ArticleId]) -> None:
    """Réécrit dernier coût et CMP des articles d'après le grand livre (même transaction)."""
    articles = ArticleRepository.within(uow)
    for article_id in dict.fromkeys(article_ids):
        state = replay_article(uow, article_id)
        article = articles.get(article_id)
        if (article.last_cost, article.wac) == (state.last_cost, state.wac):
            continue
        article.record_costs(last_cost=state.last_cost, wac=state.wac)
        articles.update(article)
