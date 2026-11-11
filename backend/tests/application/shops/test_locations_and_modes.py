"""UC-SOC-05 lieux (LOC-01 à 03) et modes de paiement (SET-01, SET-03)."""

import pytest

from app.application.ports.uow import UnitOfWork
from app.application.security.errors import PermissionDenied
from app.application.shops.stock_probe import LocationStock
from app.application.shops.use_cases.manage_locations import ManageLocations
from app.domain.shared.errors import Duplicate, VersionConflict
from app.domain.shared.roles import Role
from app.domain.shops.errors import LastPointOfSale, LocationHasStock, LocationInUse
from app.domain.shops.ids import LocationId, PaymentModeId
from app.domain.shops.location import LocationDetails
from app.domain.shops.payment_mode import PaymentModeDetails
from app.domain.shops.values import LocationKind
from tests.application.shops.support import World


class StockAt(LocationStock):
    def __init__(self, *locations: LocationId) -> None:
        self.locations = set(locations)

    def has_stock(self, uow: UnitOfWork, location_id: LocationId) -> bool:
        return location_id in self.locations


def store(name: str) -> LocationDetails:
    return LocationDetails(name=name, kind=LocationKind.STORE, is_point_of_sale=True)


def test_create_rename_and_unique_name() -> None:
    world = World()
    owner = world.owner(world.open_motos())
    wanted = LocationId.new()
    created, fresh = world.http.locations.create(owner, store("Maroua"), wanted)
    replay, again = world.http.locations.create(owner, store("Maroua"), wanted)
    assert (fresh, again, replay.id) == (True, False, created.id)
    with pytest.raises(Duplicate):
        world.http.locations.create(owner, store("  maroua "))
    renamed = world.http.locations.update(owner, created.id, {"name": "Maroua centre"}, 1)
    assert (renamed.name, renamed.version) == ("Maroua centre", 2)
    with pytest.raises(VersionConflict):
        world.http.locations.update(owner, created.id, {"name": "X"}, 1)
    assert world.http.locations.update(owner, created.id, {}, 2).version == 2
    assert {e.action.value for e in world.journal(world.shop_of(owner))} >= {"create", "update"}


def test_withdrawal_rules() -> None:
    world = World()
    owner = world.owner(world.open_motos())
    shop = world.shop_of(owner)
    garoua = world.location(shop, "Garoua")
    with pytest.raises(LastPointOfSale):
        world.http.locations.update(owner, garoua.id, {"is_point_of_sale": False}, 1)
    with pytest.raises(LastPointOfSale):
        world.http.locations.update(owner, garoua.id, {"active": False}, 1)
    second, _ = world.http.locations.create(owner, store("Maroua"))
    with pytest.raises(LocationInUse) as reception:
        world.http.locations.update(owner, garoua.id, {"active": False}, 1)
    assert reception.value.details["usage"] == "reception_location"
    world.add(owner, "677000002", Role.SELLER, "Maroua")
    with pytest.raises(LocationInUse) as seller:
        world.http.locations.update(owner, second.id, {"active": False}, 1)
    assert seller.value.details["usage"] == "default_location"
    depot = world.location(shop, "Ngaoundéré")
    stocked = ManageLocations(
        world.core.shop_uow_factory, world.http.locations._policy, StockAt(depot.id), world.clock
    )
    with pytest.raises(LocationHasStock):
        stocked.update(owner, depot.id, {"active": False}, 1)
    assert world.http.locations.update(owner, depot.id, {"active": False}, 1).active is False


def test_location_read_access_by_role() -> None:
    world = World()
    owner = world.owner(world.open_motos())
    accountant = world.member(owner, "677000003", Role.ACCOUNTANT)
    seller = world.member(owner, "677000002", Role.SELLER, "Garoua")
    assert world.http.locations.list(owner).read_only is False
    listed = world.http.locations.list(accountant)
    assert (len(listed.items), listed.read_only) == (3, True)
    with pytest.raises(PermissionDenied):
        world.http.locations.list(seller)
    with pytest.raises(PermissionDenied):
        world.http.locations.create(accountant, store("X"))


def test_payment_modes() -> None:
    world = World()
    owner = world.owner(world.open_motos())
    seller = world.member(owner, "677000002", Role.SELLER, "Garoua")
    wave = PaymentModeDetails(name="Wave", reference_required=True, display_order=7)
    mode_id = PaymentModeId.new()
    mode, created = world.http.payment_modes.create(owner, wave, mode_id)
    assert created
    assert world.http.payment_modes.create(owner, wave, mode_id)[1] is False
    assert "Wave" in [m.name for m in world.http.payment_modes.list(seller)]
    off = world.http.payment_modes.update(owner, mode.id, {"active": False}, 1)
    assert not off.details.active
    assert "Wave" not in [m.name for m in world.http.payment_modes.list(seller)]
    assert "Wave" in [m.name for m in world.http.payment_modes.list(owner)]
    assert world.http.payment_modes.update(owner, mode.id, {}, 2).version == 2
    with pytest.raises(PermissionDenied):
        world.http.payment_modes.create(seller, wave)
    configured = [e for e in world.journal(world.shop_of(owner)) if e.action.value == "configure"]
    assert [c.field for c in configured[0].changes] == ["active"]
