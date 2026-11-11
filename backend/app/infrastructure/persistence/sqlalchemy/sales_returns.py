"""Adaptateurs SQL des demandes de prix et des retours (T16b), gabarit `SqlListing`.

Les lignes rendues sont une colonne JSON (`lines`) : quantités en chaînes décimales (exactes),
montants en entiers ; les totaux du retour sont recopiés en colonnes pour les rapports (T19).
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

import sqlalchemy as sa

from app.application.sales.return_ports import PriceRequestRepository, SaleReturnRepository
from app.domain.catalog.ids import ArticleId
from app.domain.sales.ids import PriceRequestId, SaleId, SaleReturnId
from app.domain.sales.price_request import PriceRequest, PriceRequestStatus
from app.domain.sales.return_lines import ReturnedLine
from app.domain.sales.sale_return import Refund, SaleReturn
from app.domain.shared.ids import ShopId, UserId
from app.domain.shared.money import Money
from app.domain.shared.quantity import Quantity, StockUnit
from app.domain.shops.ids import LocationId, PaymentModeId
from app.infrastructure.persistence.sqlalchemy import tables_sales_returns as t
from app.infrastructure.persistence.sqlalchemy.columns import from_db, from_db_optional, to_db
from app.infrastructure.persistence.sqlalchemy.shops import SqlListing

_OPEN = (PriceRequestStatus.PENDING.value, PriceRequestStatus.ACCEPTED.value)


def _amount(value: Money | None) -> int | None:
    return None if value is None else value.amount


def _money(value: Any) -> Money | None:
    return None if value is None else Money(int(value))


class SqlPriceRequestRepository(SqlListing[PriceRequestId, PriceRequest], PriceRequestRepository):
    table = t.price_request

    def _to_columns(self, aggregate: PriceRequest) -> dict[str, Any]:
        decided, by, sale = aggregate.decided_at, aggregate.decided_by, aggregate.sale_id
        return {
            "seller_id": aggregate.seller_id.value,
            "article_id": aggregate.article_id.value,
            "article_name": aggregate.article_name,
            "location_id": aggregate.location_id.value,
            "requested_price": aggregate.requested_price.amount,
            "min_price": aggregate.min_price.amount,
            "status": aggregate.status.value,
            "requested_at": to_db(aggregate.requested_at),
            "expires_at": to_db(aggregate.expires_at),
            "decided_by": None if by is None else by.value,
            "decided_at": None if decided is None else to_db(decided),
            "sale_id": None if sale is None else sale.value,
        }

    def _from_row(self, row: sa.RowMapping) -> PriceRequest:
        by, sale = row["decided_by"], row["sale_id"]
        return PriceRequest(
            id=PriceRequestId(row["id"]),
            shop_id=ShopId(row["shop_id"]),
            seller_id=UserId(row["seller_id"]),
            article_id=ArticleId(row["article_id"]),
            article_name=row["article_name"],
            location_id=LocationId(row["location_id"]),
            requested_price=Money(int(row["requested_price"])),
            min_price=Money(int(row["min_price"])),
            requested_at=from_db(row["requested_at"]),
            expires_at=from_db(row["expires_at"]),
            status=PriceRequestStatus(row["status"]),
            decided_by=None if by is None else UserId(by),
            decided_at=from_db_optional(row["decided_at"]),
            sale_id=None if sale is None else SaleId(sale),
            version=int(row["version"]),
        )

    def _recent(self, *conditions: Any) -> list[PriceRequest]:
        c = self.table.c
        return self._select_all(c.requested_at.desc(), c.id.desc(), where=sa.and_(*conditions))

    def for_seller(self, seller: UserId) -> list[PriceRequest]:
        return self._recent(self.table.c.seller_id == seller.value)

    def pending(self) -> list[PriceRequest]:
        return self._recent(self.table.c.status == PriceRequestStatus.PENDING.value)

    def due_for_expiry(self, now: datetime) -> list[PriceRequest]:
        c = self.table.c
        open_ = sa.or_(
            c.status == PriceRequestStatus.PENDING.value,
            sa.and_(c.status == PriceRequestStatus.ACCEPTED.value, c.sale_id.is_(None)),
        )
        return self._recent(c.status.in_(_OPEN), open_, c.expires_at <= to_db(now))


def _line_json(line: ReturnedLine) -> dict[str, Any]:
    return {
        "line": line.line,
        "article_id": str(line.article_id),
        "article_name": line.article_name,
        "quantity": str(line.quantity),
        "stock_quantity": str(line.stock_quantity.value),
        "stock_unit": line.stock_quantity.unit.value,
        "condition": line.condition.value,
        "amount": line.amount.amount,
        "cost": _amount(line.cost),
        "cost_wac": _amount(line.cost_wac),
        "chassis": list(line.chassis),
    }


def _line_of(data: dict[str, Any]) -> ReturnedLine:
    return ReturnedLine(
        line=int(data["line"]),
        article_id=ArticleId.parse(data["article_id"]),
        article_name=data["article_name"],
        quantity=Decimal(data["quantity"]),
        stock_quantity=Quantity.of(data["stock_quantity"], StockUnit(data["stock_unit"])),
        condition=data["condition"],
        amount=Money(int(data["amount"])),
        cost=_money(data["cost"]),
        cost_wac=_money(data["cost_wac"]),
        chassis=tuple(data["chassis"]),
    )


class SqlSaleReturnRepository(SqlListing[SaleReturnId, SaleReturn], SaleReturnRepository):
    table = t.sale_return

    def _to_columns(self, aggregate: SaleReturn) -> dict[str, Any]:
        refund, exchange = aggregate.refund, aggregate.exchange_sale_id
        return {
            "sale_id": aggregate.sale_id.value,
            "sale_number": aggregate.sale_number,
            "kind": aggregate.kind.value,
            "lines": [_line_json(line) for line in aggregate.lines],
            "reason": aggregate.reason,
            "amount": aggregate.amount.amount,
            "margin": _amount(aggregate.margin),
            "margin_wac": _amount(aggregate.margin_wac),
            "refund_amount": None if refund is None else refund.amount.amount,
            "refund_mode_id": None if refund is None else refund.mode_id.value,
            "refunded_on": None if refund is None else refund.refunded_on,
            "credit_reduction": aggregate.credit_reduction.amount,
            "exchange_sale_id": None if exchange is None else exchange.value,
            "returned_at": to_db(aggregate.returned_at),
            "returned_on": aggregate.returned_on,
            "created_by": aggregate.created_by.value,
        }

    def _from_row(self, row: sa.RowMapping) -> SaleReturn:
        amount, exchange = row["refund_amount"], row["exchange_sale_id"]
        return SaleReturn(
            id=SaleReturnId(row["id"]),
            shop_id=ShopId(row["shop_id"]),
            sale_id=SaleId(row["sale_id"]),
            sale_number=row["sale_number"],
            kind=row["kind"],
            lines=tuple(_line_of(item) for item in row["lines"]),
            reason=row["reason"],
            returned_at=from_db(row["returned_at"]),
            created_by=UserId(row["created_by"]),
            refund=None
            if amount is None
            else Refund(
                amount=Money(int(amount)),
                mode_id=PaymentModeId(row["refund_mode_id"]),
                refunded_on=row["refunded_on"],
            ),
            credit_reduction=Money(int(row["credit_reduction"])),
            exchange_sale_id=None if exchange is None else SaleId(exchange),
            version=int(row["version"]),
        )

    def for_sale(self, sale_id: SaleId) -> list[SaleReturn]:
        c = self.table.c
        return self._select_all(c.returned_at, c.id, where=c.sale_id == sale_id.value)

    def between(self, first_day: date, last_day: date) -> list[SaleReturn]:
        c = self.table.c
        where = sa.and_(c.returned_on >= first_day, c.returned_on <= last_day)
        return self._select_all(c.returned_at, c.id, where=where)


SQL_SALES_RETURNS_REPOSITORIES = (SqlPriceRequestRepository, SqlSaleReturnRepository)
