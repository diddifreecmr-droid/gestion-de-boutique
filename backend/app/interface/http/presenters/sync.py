"""Présentation de la synchronisation hors connexion (T23, specs § 6.5).

Instantané : prix de vente selon `CatalogVisibility` (minimum masqué → `null`) ; **aucun**
coût, quel que soit le rôle (le schéma n'a pas ces clés, SEC-N01).
"""

from app.application.sync.inputs import OperationNotice, OperationResult
from app.application.sync.use_cases.offline_snapshot import OfflineSnapshot
from app.domain.catalog.article import Article
from app.domain.catalog.prices import MINIMUM_KINDS, PriceKind
from app.interface.http.presenters.expenses import category_response
from app.interface.http.presenters.receipts import customer_response
from app.interface.http.presenters.shops import location_response, payment_mode_response
from app.interface.http.schemas.sync import (
    OfflineSnapshotResponse,
    SnapshotArticleResponse,
    SyncNoticeResponse,
    SyncResponse,
    SyncResultResponse,
)


def _notice(notice: OperationNotice) -> SyncNoticeResponse:
    return SyncNoticeResponse(
        code=notice.code, message=notice.message, details=dict(notice.details)
    )


def sync_response(results: list[OperationResult]) -> SyncResponse:
    return SyncResponse(
        results=[
            SyncResultResponse(
                op_id=str(r.op_id),
                status=r.status.value,
                provisional_number=r.provisional_number,
                number=r.number,
                entity_id=None if r.entity_id is None else str(r.entity_id),
                warnings=[_notice(w) for w in r.warnings],
                error=None if r.error is None else _notice(r.error),
            )
            for r in results
        ]
    )


def _price(article: Article, kind: PriceKind, visible: bool) -> int | None:
    price = article.prices.of(kind) if visible else None
    return None if price is None else price.amount


def snapshot_article(article: Article, selling: bool, minimum: bool) -> SnapshotArticleResponse:
    fields = article.details.fields
    shown = {kind: selling and (kind not in MINIMUM_KINDS or minimum) for kind in PriceKind}
    return SnapshotArticleResponse(
        id=str(article.id),
        display_name=fields.display_name,
        reference=fields.reference,
        stock_unit=fields.stock_unit.value,
        sold_by_piece=fields.sold_by_piece,
        base_price=_price(article, PriceKind.BASE, shown[PriceKind.BASE]),
        base_price_piece=_price(article, PriceKind.BASE_PIECE, shown[PriceKind.BASE_PIECE]),
        min_price=_price(article, PriceKind.MINIMUM, shown[PriceKind.MINIMUM]),
        min_price_piece=_price(article, PriceKind.MINIMUM_PIECE, shown[PriceKind.MINIMUM_PIECE]),
    )


def snapshot_response(snapshot: OfflineSnapshot) -> OfflineSnapshotResponse:
    visibility = snapshot.visibility
    return OfflineSnapshotResponse(
        generated_at=snapshot.generated_at,
        since=snapshot.since,
        full=True,
        min_price_enabled=snapshot.min_price_enabled,
        articles=[
            snapshot_article(a, visibility.selling_prices, visibility.min_prices)
            for a in snapshot.articles
        ],
        customers=[customer_response(c) for c in snapshot.customers],
        expense_categories=[category_response(c) for c in snapshot.expense_categories],
        locations=[location_response(loc) for loc in snapshot.locations],
        payment_modes=[payment_mode_response(m) for m in snapshot.payment_modes],
    )
