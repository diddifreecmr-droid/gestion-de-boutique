"""`MembershipDirectory` mémoire : rattachements saisis par les tests et la démo.

Provisoire : T10 créera l'agrégat `MEMBERSHIP` (rôle, lieu habituel, activation) et un
adaptateur qui lira ses dépôts ; ce répertoire ne sert alors plus qu'aux tests.
"""

import threading
from collections.abc import Sequence
from dataclasses import replace

from app.application.identity.ports import MembershipDirectory, MembershipView
from app.application.security.roles import Role
from app.domain.shared.errors import Duplicate
from app.domain.shared.ids import ShopId, UserId


class InMemoryMembershipDirectory(MembershipDirectory):
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._rows: dict[tuple[UserId, ShopId], MembershipView] = {}

    def grant(self, user_id: UserId, shop_id: ShopId, shop_name: str, role: Role) -> None:
        """Un seul rattachement par utilisateur et par boutique (CDC § 20.1)."""
        with self._lock:
            if (user_id, shop_id) in self._rows:
                msg = "Utilisateur déjà rattaché à cette boutique"
                raise Duplicate(msg, details={"constraint": "membership_user_shop"})
            self._rows[(user_id, shop_id)] = MembershipView(
                shop_id=shop_id, shop_name=shop_name, role=role, active=True
            )

    def set_active(self, user_id: UserId, shop_id: ShopId, *, active: bool) -> None:
        with self._lock:
            current = self._rows[(user_id, shop_id)]  # KeyError : rattachement inexistant
            self._rows[(user_id, shop_id)] = replace(current, active=active)

    def for_user(self, user_id: UserId) -> Sequence[MembershipView]:
        with self._lock:
            views = [view for (owner, _), view in self._rows.items() if owner == user_id]
        return sorted(views, key=lambda view: (view.shop_name, view.shop_id))

    def find(self, user_id: UserId, shop_id: ShopId) -> MembershipView | None:
        with self._lock:
            return self._rows.get((user_id, shop_id))
