"""Contrat `EntitlementOverrides` : poser, remplacer, retirer ; par boutique et par droit."""

from datetime import timedelta

from app.application.plans.ports import EntitlementOverride
from app.domain.plans.entitlements import Entitlement
from app.domain.shared.ids import ShopId, UserId
from tests.contracts.backends import ContractBackend
from tests.contracts.widget import NOW

ADMIN = UserId.new()
OFFLINE = Entitlement.OFFLINE_CAPTURE


def override(shop: ShopId, *, enabled: bool, minutes: int = 0) -> EntitlementOverride:
    return EntitlementOverride(
        shop_id=shop,
        entitlement=OFFLINE,
        enabled=enabled,
        set_by=ADMIN,
        set_at=NOW + timedelta(minutes=minutes),
    )


def test_put_find_replace_remove(backend: ContractBackend, shop_a: ShopId, shop_b: ShopId) -> None:
    store = backend.entitlement_overrides()
    assert store.find(shop_a, OFFLINE) is None
    store.put(override(shop_a, enabled=True))
    assert store.find(shop_a, OFFLINE) == override(shop_a, enabled=True)
    assert store.find(shop_b, OFFLINE) is None  # par boutique
    store.put(override(shop_a, enabled=False, minutes=5))
    assert store.find(shop_a, OFFLINE) == override(shop_a, enabled=False, minutes=5)
    assert store.remove(shop_a, OFFLINE) is True
    assert store.remove(shop_a, OFFLINE) is False
    assert store.find(shop_a, OFFLINE) is None
