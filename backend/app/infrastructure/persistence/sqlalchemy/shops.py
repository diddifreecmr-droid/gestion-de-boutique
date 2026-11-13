"""Dépôts SQL du socle (1/2) : boutique, réglages, lieux (T10)."""

from decimal import Decimal
from typing import Any

import sqlalchemy as sa

from app.application.ports.aggregate import Aggregate
from app.application.ports.repository import not_found
from app.application.shops.ports import (
    LocationRepository,
    ShopRepository,
    ShopSettingsRepository,
)
from app.domain.identity.phone import PhoneNumber
from app.domain.profiles.modules import Module
from app.domain.profiles.printing import ReceiptFormat
from app.domain.profiles.profile import ProfileCode
from app.domain.shared.ids import EntityId, ShopId
from app.domain.shops.ids import LocationId, MerchantAccountId, ShopSettingsId
from app.domain.shops.location import Location, LocationDetails
from app.domain.shops.settings import SettingsValues, ShopSettings
from app.domain.shops.shop import Shop, ShopIdentity
from app.domain.shops.values import LocationKind, ShopStatus
from app.infrastructure.persistence.sqlalchemy import tables_shops as t
from app.infrastructure.persistence.sqlalchemy.columns import from_db, to_db
from app.infrastructure.persistence.sqlalchemy.repository import SqlRepository


class SqlListing[IdT: EntityId, AggT: Aggregate](SqlRepository[IdT, AggT]):
    def _select_all(self, *order_by: Any, where: Any = None) -> list[AggT]:
        statement = sa.select(self.table).where(self.table.c.shop_id == self.shop_id.value)
        if where is not None:
            statement = statement.where(where)
        rows = self._transaction.fetch_all(statement.order_by(*order_by))
        aggregates = [self._from_row(row) for row in rows]
        for aggregate in aggregates:
            self._tracker.track(aggregate, saved=False)
        return aggregates


class SqlShopRepository(SqlListing[ShopId, Shop], ShopRepository):
    table = t.shop

    def _to_columns(self, aggregate: Shop) -> dict[str, Any]:
        identity = aggregate.identity
        return {
            "account_id": aggregate.account_id.value,
            "name": identity.name,
            "profile_code": aggregate.profile_code.value,
            "city": identity.city,
            "phone": identity.phone.e164,
            "address": identity.address,
            "niu": identity.niu,
            "rccm": identity.rccm,
            "enabled_modules": sorted(module.value for module in aggregate.enabled_modules),
            "status": aggregate.status.value,
            "created_at": to_db(aggregate.created_at),
        }

    def _from_row(self, row: sa.RowMapping) -> Shop:
        return shop_from_row(row, version=int(row["version"]))


def shop_from_row(row: sa.RowMapping, *, version: int) -> Shop:
    """Aussi utilisé par les lectures plateforme (`directories.py`)."""
    return Shop(
        id=ShopId(row["id"]),
        account_id=MerchantAccountId(row["account_id"]),
        profile_code=ProfileCode(row["profile_code"]),
        identity=ShopIdentity(
            name=row["name"],
            city=row["city"],
            phone=PhoneNumber(row["phone"]),
            address=row["address"],
            niu=row["niu"],
            rccm=row["rccm"],
        ),
        enabled_modules=frozenset(Module(m) for m in row["enabled_modules"]),
        status=ShopStatus(row["status"]),
        created_at=from_db(row["created_at"]),
        version=version,
    )


class SqlShopSettingsRepository(SqlListing[ShopSettingsId, ShopSettings], ShopSettingsRepository):
    table = t.shop_settings

    def _to_columns(self, aggregate: ShopSettings) -> dict[str, Any]:
        values = aggregate.values
        location = values.reception_location_id
        return {
            "receipt_format": values.receipt_format.value,
            "paper_width_mm": values.paper_width_mm,
            "printable_width_mm": values.printable_width_mm,
            "margin_mm": values.margin_mm,
            "font_size_pt": values.font_size_pt,
            "show_logo": values.show_logo,
            "footer_message": values.footer_message,
            "copies": values.copies,
            "low_stock_threshold": values.low_stock_threshold,
            "min_price_enabled": values.min_price_enabled,
            "min_price_requires_approval": values.min_price_requires_approval,
            "exchange_days": values.exchange_days,
            "employee_exchange_allowed": values.employee_exchange_allowed,
            "truck_silent_hours": values.truck_silent_hours,
            "transfer_in_transit_days": values.transfer_in_transit_days,
            "reception_location_id": None if location is None else location.value,
        }

    def _from_row(self, row: sa.RowMapping) -> ShopSettings:
        location = row["reception_location_id"]
        values = SettingsValues(
            receipt_format=ReceiptFormat(row["receipt_format"]),
            paper_width_mm=int(row["paper_width_mm"]),
            printable_width_mm=int(row["printable_width_mm"]),
            margin_mm=int(row["margin_mm"]),
            font_size_pt=int(row["font_size_pt"]),
            show_logo=bool(row["show_logo"]),
            footer_message=row["footer_message"],
            copies=int(row["copies"]),
            low_stock_threshold=Decimal(str(row["low_stock_threshold"])),
            min_price_enabled=bool(row["min_price_enabled"]),
            min_price_requires_approval=bool(row["min_price_requires_approval"]),
            exchange_days=row["exchange_days"],
            employee_exchange_allowed=bool(row["employee_exchange_allowed"]),
            truck_silent_hours=row["truck_silent_hours"],
            transfer_in_transit_days=row["transfer_in_transit_days"],
            reception_location_id=None if location is None else LocationId(location),
        )
        return ShopSettings(
            id=ShopSettingsId(row["id"]),
            shop_id=ShopId(row["shop_id"]),
            values=values,
            version=int(row["version"]),
        )

    def current(self) -> ShopSettings:
        found = self._select_all(self.table.c.id)
        if not found:
            raise not_found(self.shop_id)
        return found[0]


class SqlLocationRepository(SqlListing[LocationId, Location], LocationRepository):
    table = t.location

    def _to_columns(self, aggregate: Location) -> dict[str, Any]:
        details = aggregate.details
        return {
            "name": details.name,
            "name_key": aggregate.name_key,
            "kind": details.kind.value,
            "is_point_of_sale": details.is_point_of_sale,
            "city": details.city,
            "display_order": details.display_order,
            "active": details.active,
        }

    def _from_row(self, row: sa.RowMapping) -> Location:
        details = LocationDetails(
            name=row["name"],
            kind=LocationKind(row["kind"]),
            is_point_of_sale=bool(row["is_point_of_sale"]),
            city=row["city"],
            display_order=int(row["display_order"]),
            active=bool(row["active"]),
        )
        return Location(
            id=LocationId(row["id"]),
            shop_id=ShopId(row["shop_id"]),
            details=details,
            version=int(row["version"]),
        )

    def list_all(self) -> list[Location]:
        c = self.table.c
        return self._select_all(c.display_order, c.name_key, c.id)
