"""`EntitlementOverrides` SQL : table `entitlement_override`, une transaction courte par appel.

Écriture portable (aucun `ON CONFLICT` propre à un moteur) : `UPDATE` de la ligne ; si elle
n'existe pas, `INSERT`. Une création concurrente du même couple viole la clé primaire : on
rejoue alors l'`UPDATE`, une seule fois (la ligne existe forcément) ; tout autre échec remonte.
"""

import sqlalchemy as sa

from app.application.plans.ports import EntitlementOverride, EntitlementOverrides
from app.domain.plans.entitlements import Entitlement
from app.domain.shared.ids import ShopId, UserId
from app.infrastructure.persistence.sqlalchemy.columns import from_db, to_db
from app.infrastructure.persistence.sqlalchemy.tables import entitlement_override as table


def _key(shop_id: ShopId, entitlement: Entitlement) -> sa.ColumnElement[bool]:
    return sa.and_(table.c.shop_id == shop_id.value, table.c.entitlement == entitlement.value)


class SqlEntitlementOverrides(EntitlementOverrides):
    def __init__(self, engine: sa.Engine) -> None:
        self._engine = engine

    def find(self, shop_id: ShopId, entitlement: Entitlement) -> EntitlementOverride | None:
        with self._engine.connect() as connection:
            row = (
                connection.execute(sa.select(table).where(_key(shop_id, entitlement)))
                .mappings()
                .first()
            )
        if row is None:
            return None
        return EntitlementOverride(
            shop_id=shop_id,
            entitlement=entitlement,
            enabled=bool(row["enabled"]),
            set_by=UserId(row["set_by"]),
            set_at=from_db(row["set_at"]),
        )

    def put(self, override: EntitlementOverride) -> None:
        values = {
            "enabled": override.enabled,
            "set_by": override.set_by.value,
            "set_at": to_db(override.set_at),
        }
        update = sa.update(table).where(_key(override.shop_id, override.entitlement)).values(values)
        with self._engine.begin() as connection:
            if connection.execute(update).rowcount == 1:
                return
            insert = sa.insert(table).values(
                shop_id=override.shop_id.value, entitlement=override.entitlement.value, **values
            )
            try:
                with connection.begin_nested():
                    connection.execute(insert)
            except sa.exc.IntegrityError:
                # Seule cause attendue : création concurrente du même couple. L'UPDATE rejoué
                # échoue bruyamment si la ligne n'existe toujours pas.
                if connection.execute(update).rowcount != 1:
                    raise

    def remove(self, shop_id: ShopId, entitlement: Entitlement) -> bool:
        with self._engine.begin() as connection:
            return (
                connection.execute(sa.delete(table).where(_key(shop_id, entitlement))).rowcount == 1
            )
