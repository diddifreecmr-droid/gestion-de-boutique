"""Présentation du stock **selon le rôle** (TR-05, RG-D02, RG-D03, SEC-N01, SEC-N02).

Un champ invisible n'est pas posé : la route sérialise sans les champs non posés, la clé
n'existe pas dans le JSON. La décision vient de `StockVisibility` (application).
"""

from typing import Any

from app.application.stock.adjusting import AdjustmentResult
from app.application.stock.use_cases.stock_history import DamagedStock, MovementHistory
from app.application.stock.use_cases.stock_matrix import MatrixRow, StockMatrix
from app.application.stock.use_cases.stock_value import StockValueReport
from app.application.stock.use_cases.stock_value import Valuation as ValuationData
from app.application.stock.visibility import StockVisibility
from app.domain.catalog.article import Article
from app.domain.shared.money import Money
from app.domain.shared.quantity import Quantity
from app.domain.stock.movement import StockMovement
from app.domain.stock.valuation import value_of
from app.domain.stock.values import SourceType
from app.interface.http.schemas import stock as s


def amount(value: Money | None) -> int | None:
    return None if value is None else value.amount


def _costs(article: Article, visibility: StockVisibility) -> dict[str, Any]:
    if not visibility.costs:
        return {}
    return {"last_cost": amount(article.last_cost), "wac": amount(article.wac)}


def _row(row: MatrixRow, visibility: StockVisibility) -> s.StockRow:
    article = row.article
    extra = _costs(article, visibility)
    if visibility.costs:
        sellable = sum((c.sellable for c in row.cells), Quantity.zero(row.total.unit))
        extra["wac_value"] = amount(value_of(sellable, article.wac))
    if visibility.selling_prices:
        extra["base_price"] = amount(article.prices.base_price)
    return s.StockRow(
        article_id=str(article.id),
        display_name=article.display_name,
        stock_unit=article.details.fields.stock_unit.value,
        cells=[
            s.StockCell(
                location_id=str(cell.location_id),
                sellable=str(cell.sellable),
                damaged=str(cell.damaged),
            )
            for cell in row.cells
        ],
        incoming=str(row.incoming),
        total=str(row.total),
        stock_status=row.badge.value,
        alert_threshold=str(row.threshold),
        **extra,
    )


def matrix_response(matrix: StockMatrix) -> s.StockMatrixResponse:
    return s.StockMatrixResponse(
        locations=[
            s.StockColumn(
                location_id=str(loc.id),
                name=loc.name,
                kind=loc.details.kind.value,
                is_point_of_sale=loc.details.is_point_of_sale,
            )
            for loc in matrix.locations
        ],
        items=[_row(row, matrix.visibility) for row in matrix.rows],
    )


def valuation_response(data: ValuationData) -> s.Valuation:
    return s.Valuation(
        at_wac=amount(data.at_wac),
        at_wac_known=data.at_wac_known.amount,
        without_wac=data.without_wac,
        at_last_cost=amount(data.at_last_cost),
        at_last_cost_known=data.at_last_cost_known.amount,
        without_last_cost=data.without_last_cost,
    )


def value_response(report: StockValueReport) -> s.StockValueResponse:
    return s.StockValueResponse(
        locations=[
            s.LocationValuation(
                location_id=str(line.location.id),
                location_name=line.location.name,
                active=line.location.active,
                sellable=valuation_response(line.sellable),
                damaged=valuation_response(line.damaged),
                incoming=valuation_response(line.incoming),
            )
            for line in report.locations
        ],
        sellable=valuation_response(report.sellable),
        damaged=valuation_response(report.damaged),
        incoming=valuation_response(report.incoming),
    )


def damaged_response(stock: DamagedStock) -> s.DamagedStockResponse:
    items = []
    for line in stock.lines:
        extra: dict[str, Any] = {}
        if stock.visibility.costs:
            extra["wac"] = amount(line.article.wac)
            extra["wac_value"] = amount(value_of(line.level.damaged, line.article.wac))
        items.append(
            s.DamagedLine(
                article_id=str(line.article.id),
                display_name=line.article.display_name,
                stock_unit=line.article.details.fields.stock_unit.value,
                location_id=str(line.location.id),
                location_name=line.location.name,
                damaged=str(line.level.damaged),
                **extra,
            )
        )
    return s.DamagedStockResponse(items=items)


def _document(movement: StockMovement, visibility: StockVisibility) -> s.MovementDocument:
    source = movement.source
    hidden = source.type is SourceType.SALE and not visibility.sales_documents
    return s.MovementDocument(
        type=source.type.value,
        id=None if hidden else str(source.id),
        number=None if hidden else source.number,
    )


def movements_response(history: MovementHistory) -> s.MovementListResponse:
    items = []
    for m in history.page.items:
        location = history.locations.get(m.location_id)
        extra = {"unit_cost": amount(m.unit_cost)} if history.visibility.costs else {}
        items.append(
            s.MovementResponse(
                id=str(m.id),
                type=m.type.value,
                type_label=m.type.label,
                location_id=str(m.location_id),
                location_name="?" if location is None else location.name,
                condition=m.condition.value,
                quantity=str(m.quantity),
                balance_after=str(m.balance_after),
                document=_document(m, history.visibility),
                occurred_at=m.occurred_at,
                recorded_at=m.recorded_at,
                author_id=str(m.author_id),
                stock_to_verify=m.stock_to_verify,
                reverses_id=None if m.reverses is None else str(m.reverses),
                **extra,
            )
        )
    cursor = history.page.next_cursor
    return s.MovementListResponse(
        article_id=str(history.article.id),
        stock_unit=history.article.details.fields.stock_unit.value,
        items=items,
        next_cursor=None if cursor is None else cursor.encode(),
    )


def adjustment_response(result: AdjustmentResult) -> s.AdjustmentResponse:
    a, movement = result.adjustment, result.movement
    return s.AdjustmentResponse(
        id=str(a.id),
        location_id=str(a.location_id),
        article_id=str(a.article_id),
        direction=a.direction.value,
        quantity=str(a.quantity),
        condition=a.condition.value,
        reason=a.reason.value,
        note=a.note,
        photo_id=None if a.photo_id is None else str(a.photo_id),
        inventory_id=None if a.inventory_id is None else str(a.inventory_id),
        created_at=a.created_at,
        author_id=str(a.author_id),
        balance_after=None if movement is None else str(movement.balance_after),
    )
