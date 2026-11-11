"""Présentation du socle des boutiques (TR-05).

Aucun champ de coût ni de vente ici. La route décide déjà qui voit quoi (membres : propriétaire
seul ; lieux : propriétaire et comptable, celui-ci en lecture → `read_only`).
"""

from app.application.shops.ports import ShopSummary
from app.application.shops.use_cases.get_shop_profile import ShopProfileView
from app.application.shops.use_cases.member_views import MemberView
from app.domain.profiles.fields import FieldSpec
from app.domain.profiles.menus import MenuEntry
from app.domain.profiles.printing import print_profile_of
from app.domain.shops.location import Location
from app.domain.shops.payment_mode import PaymentMode
from app.domain.shops.settings import SettingsValues
from app.domain.shops.shop import Shop
from app.interface.http.schemas.members import MemberResponse
from app.interface.http.schemas.places import LocationResponse, PaymentModeResponse
from app.interface.http.schemas.platform import ShopSummaryResponse
from app.interface.http.schemas.shop import (
    FieldResponse,
    MenuEntryResponse,
    ProfileResponse,
    ReceiptSettingsResponse,
    RoleResponse,
    SettingsResponse,
    ShopHeaderResponse,
)


def summary_response(summary: ShopSummary) -> ShopSummaryResponse:
    return ShopSummaryResponse(
        shop_id=str(summary.shop_id),
        name=summary.name,
        profile_code=summary.profile_code.value,
        city=summary.city,
        status=summary.status.value,
        enabled_modules=sorted(m.value for m in summary.enabled_modules),
        account_id=str(summary.account_id),
        account_name=summary.account_name,
        plan=summary.plan.value,
        created_at=summary.created_at,
    )


def header_response(shop: Shop) -> ShopHeaderResponse:
    identity = shop.identity
    return ShopHeaderResponse(
        name=identity.name,
        city=identity.city,
        phone=identity.phone.e164,
        address=identity.address,
        niu=identity.niu,
        rccm=identity.rccm,
    )


def _menu(entry: MenuEntry) -> MenuEntryResponse:
    return MenuEntryResponse(
        code=entry.code,
        label=entry.label,
        module=entry.module.value,
        children=[_menu(child) for child in entry.children],
    )


def _field(spec: FieldSpec) -> FieldResponse:
    return FieldResponse(
        code=spec.code,
        label=spec.label,
        kind=spec.kind.value,
        required=spec.required,
        unique=spec.unique,
        choices=list(spec.choices),
    )


def _receipt(shop: Shop, values: SettingsValues) -> ReceiptSettingsResponse:
    return ReceiptSettingsResponse(
        format=values.receipt_format.value,
        print_profile=print_profile_of(values.receipt_format).code.value,
        paper_width_mm=values.paper_width_mm,
        printable_width_mm=values.printable_width_mm,
        margin_mm=values.margin_mm,
        font_size_pt=values.font_size_pt,
        show_logo=values.show_logo,
        copies=values.copies,
        footer_message=values.footer_message,
        header=header_response(shop),
    )


def profile_response(view: ShopProfileView) -> ProfileResponse:
    profile, shop = view.profile, view.shop
    location = view.default_location_id
    return ProfileResponse(
        shop_id=str(shop.id),
        profile_code=profile.code.value,
        profile_version=profile.version,
        profile_label=profile.label,
        enabled_modules=sorted(m.value for m in shop.enabled_modules),
        roles=[RoleResponse(code=r.value, label=profile.role_label(r)) for r in profile.roles],
        role=None if view.role is None else view.role.value,
        role_label=None if view.role is None else profile.role_label(view.role),
        menu=[_menu(entry) for entry in view.menu],
        article_fields=[_field(spec) for spec in profile.article_fields],
        sale_fields=[_field(spec) for spec in profile.sale_fields],
        stock_units=[unit.value for unit in profile.stock_units],
        receipt=_receipt(shop, view.settings),
        min_price_enabled=view.settings.min_price_enabled,
        default_location_id=None if location is None else str(location),
    )


def settings_response(shop: Shop, values: SettingsValues, version: int) -> SettingsResponse:
    location = values.reception_location_id
    return SettingsResponse(
        version=version,
        receipt_format=values.receipt_format.value,
        print_profile=print_profile_of(values.receipt_format).code.value,
        paper_width_mm=values.paper_width_mm,
        printable_width_mm=values.printable_width_mm,
        margin_mm=values.margin_mm,
        font_size_pt=values.font_size_pt,
        show_logo=values.show_logo,
        footer_message=values.footer_message,
        copies=values.copies,
        low_stock_threshold=str(values.low_stock_threshold),
        min_price_enabled=values.min_price_enabled,
        exchange_days=values.exchange_days,
        truck_silent_hours=values.truck_silent_hours,
        transfer_in_transit_days=values.transfer_in_transit_days,
        reception_location_id=None if location is None else str(location),
        header=header_response(shop),
    )


def location_response(location: Location) -> LocationResponse:
    details = location.details
    return LocationResponse(
        id=str(location.id),
        name=details.name,
        kind=details.kind.value,
        is_point_of_sale=details.is_point_of_sale,
        city=details.city,
        display_order=details.display_order,
        active=details.active,
        version=location.version,
    )


def payment_mode_response(mode: PaymentMode) -> PaymentModeResponse:
    details = mode.details
    return PaymentModeResponse(
        id=str(mode.id),
        name=details.name,
        reference_required=details.reference_required,
        active=details.active,
        display_order=details.display_order,
        version=mode.version,
    )


def member_response(view: MemberView) -> MemberResponse:
    membership = view.membership
    location = membership.default_location_id
    return MemberResponse(
        user_id=str(membership.user_id),
        name=view.name,
        phone=view.phone,
        role=membership.role.value,
        default_location_id=None if location is None else str(location),
        active=membership.active,
        locked=view.locked,
        must_change_pin=view.must_change_pin,
        version=membership.version,
    )
