"""`EntitlementOverrides` mémoire : surcharges des droits d'offre, validées aussitôt."""

import threading

from app.application.plans.ports import EntitlementOverride, EntitlementOverrides
from app.domain.plans.entitlements import Entitlement
from app.domain.shared.ids import ShopId


class InMemoryEntitlementOverrides(EntitlementOverrides):
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._rows: dict[tuple[ShopId, Entitlement], EntitlementOverride] = {}

    def find(self, shop_id: ShopId, entitlement: Entitlement) -> EntitlementOverride | None:
        with self._lock:
            return self._rows.get((shop_id, entitlement))

    def put(self, override: EntitlementOverride) -> None:
        if not isinstance(override, EntitlementOverride):
            msg = f"EntitlementOverride attendu, reçu {type(override).__name__}"
            raise TypeError(msg)
        with self._lock:
            self._rows[(override.shop_id, override.entitlement)] = override

    def remove(self, shop_id: ShopId, entitlement: Entitlement) -> bool:
        with self._lock:
            return self._rows.pop((shop_id, entitlement), None) is not None
