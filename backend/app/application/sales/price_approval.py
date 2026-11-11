"""Prix minimum avec accord du propriétaire (UC-VEN-03 ; ERR-PRM-05 à 08 ; Q-44 tranchée).

**Seulement si le réglage `min_price_requires_approval` est vrai** (faux par défaut, décision
client specs § 15.1 : sinon la ligne est acceptée avec un avertissement, `checks.py`, et un
`price_request_id` éventuel est ignoré). Réglage vrai : une ligne d'un **vendeur** strictement
sous le minimum actif n'est acceptée qu'avec un `price_request_id` qui la couvre : demande
**Acceptée**, non expirée (horloge `Clock`), jamais utilisée, du **même vendeur**, du **même
article**, et prix de la ligne **≥ prix accordé**.
Sinon `PRICE_BELOW_MINIMUM` (`request_required: true`) avec `price_request` = la raison :
`not_found`, `other_seller`, `other_article`, `pending`, `refused`, `expired`, `used`,
`price_too_low`. Une même demande couvre toutes les lignes de son article ; une fois la vente
enregistrée, elle y est liée (`PriceRequest.use`) et ne ressert plus. La vente est alors
journalisée « sous le minimum » (sensible), comme celle du propriétaire.

Le propriétaire vend librement (la demande éventuelle est ignorée). Hors connexion : une vente
différée d'un vendeur sous le minimum est refusée par `check_minimums` quand l'accord est
exigé (RG-T18 / OFF-07), acceptée avec avertissement sinon.
"""

from collections.abc import Sequence
from datetime import datetime

from app.application.ports.uow import UnitOfWork
from app.application.sales.checks import SaleWarning, check_minimums
from app.application.sales.lines import minimum_of
from app.application.sales.return_ports import PriceRequestRepository
from app.application.security.actor import Actor
from app.application.security.roles import Role
from app.domain.catalog.article import Article
from app.domain.sales.errors import PriceBelowMinimum
from app.domain.sales.ids import PriceRequestId
from app.domain.sales.lines import SaleLine
from app.domain.sales.price_request import PriceRequest, PriceRequestStatus


def _problem(request: PriceRequest | None, actor: Actor, now: datetime) -> str | None:
    if request is None:
        return "not_found"
    if request.seller_id != actor.user_id:
        return "other_seller"
    if request.sale_id is not None:
        return "used"
    status = request.status_at(now)
    if status is not PriceRequestStatus.ACCEPTED:
        return status.value
    return None


def approve_minimums(
    uow: UnitOfWork,
    lines: Sequence[tuple[SaleLine, Article]],
    *,
    enabled: bool,
    requires_approval: bool,
    actor: Actor,
    request_id: PriceRequestId | None,
    now: datetime,
) -> tuple[bool, PriceRequest | None, list[SaleWarning]]:
    """(sous le minimum ?, demande à lier, avertissements) ; lève sur une ligne non couverte."""
    if actor.role is Role.OWNER or request_id is None or not requires_approval:
        below, warnings = check_minimums(
            lines, enabled=enabled, actor=actor, requires_approval=requires_approval
        )
        return below, None, warnings
    request = PriceRequestRepository.within(uow).find(request_id)
    problem = _problem(request, actor, now)
    used: PriceRequest | None = None
    for position, (line, article) in enumerate(lines, start=1):
        minimum = minimum_of(article, line, enabled=enabled)
        if minimum is None or line.unit_price >= minimum:
            continue
        why = problem
        if why is None and request is not None:
            if request.article_id != article.id:
                why = "other_article"
            elif line.unit_price < request.requested_price:
                why = "price_too_low"
        if why is not None or request is None:
            raise PriceBelowMinimum(
                article_id=str(article.id),
                line=position,
                min_price=minimum,
                price_request=why or "not_found",
            )
        used = request
    return used is not None, used, []
