"""Adaptateur SQL sous contrat, indépendant du moteur (PostgreSQL, SQLite des tests unitaires).

La table `widget` de l'agrégat de démonstration est créée **par le banc de tests**, jamais par
une migration de production. Les migrations réelles (`alembic upgrade head`) sont appliquées
par `migrate`, comme en production.
"""

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import sqlalchemy as sa
from alembic.config import Config

from alembic import command
from app.application.identity.ports import (
    AdminDelegationDirectory,
    IdentityEventHandler,
    MembershipDirectory,
)
from app.application.plans.ports import EntitlementOverrides
from app.application.ports.event_handler import EventHandler
from app.application.shops.ports import ShopCatalog
from app.domain.shared.ids import ShopId
from app.infrastructure.persistence.sqlalchemy.alerts import SqlAlertRepository
from app.infrastructure.persistence.sqlalchemy.audit_log import SqlAuditLog
from app.infrastructure.persistence.sqlalchemy.directories import (
    SqlAdminDelegations,
    SqlMembershipDirectory,
    SqlShopCatalog,
)
from app.infrastructure.persistence.sqlalchemy.entitlements import SqlEntitlementOverrides
from app.infrastructure.persistence.sqlalchemy.platform_uow import (
    SqlIdentityUnitOfWork,
    SqlShopJoin,
)
from app.infrastructure.persistence.sqlalchemy.repository import SqlRepository
from app.infrastructure.persistence.sqlalchemy.shops_members import SQL_SHOP_REPOSITORIES
from app.infrastructure.persistence.sqlalchemy.tables import NAMING_CONVENTION, metadata
from app.infrastructure.persistence.sqlalchemy.uow import SqlRepositoryRegistry, SqlUnitOfWork
from tests.contracts.widget import Widget, WidgetId, WidgetRepository

ALEMBIC_INI = Path(__file__).resolve().parents[3] / "alembic.ini"

test_metadata = sa.MetaData(naming_convention=NAMING_CONVENTION)

widget_table = sa.Table(
    "widget",
    test_metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("shop_id", sa.Uuid, nullable=False),
    sa.Column("label", sa.String(200), nullable=False),
    sa.Column("code", sa.String(50), nullable=True),
    sa.Column("version", sa.BigInteger, nullable=False),
    sa.UniqueConstraint("shop_id", "code", name="widget_code"),  # = UniqueKey("widget_code")
    sa.CheckConstraint("version >= 1", name="version_positive"),
)


class SqlWidgetRepository(SqlRepository[WidgetId, Widget], WidgetRepository):
    table = widget_table

    def _to_columns(self, aggregate: Widget) -> dict[str, Any]:
        return {"label": aggregate.label, "code": aggregate.code}

    def _from_row(self, row: sa.RowMapping) -> Widget:
        return Widget(
            WidgetId(row["id"]),
            ShopId(row["shop_id"]),
            row["label"],
            row["code"],
            version=int(row["version"]),
        )


SQL_REGISTRY: SqlRepositoryRegistry = (
    SqlWidgetRepository,
    SqlAuditLog,
    SqlAlertRepository,
    *SQL_SHOP_REPOSITORIES,
)


def migrate(engine: sa.Engine) -> None:
    """`alembic upgrade head` sur `engine`, puis la table de démonstration du banc."""
    config = Config(str(ALEMBIC_INI))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
    test_metadata.create_all(engine)


def wipe(engine: sa.Engine) -> None:
    """Base vierge : vide les tables touchées par les contrats (rapide, portable)."""
    with engine.begin() as connection:
        connection.execute(widget_table.delete())
        for table in metadata.sorted_tables:  # toutes les tables de production
            connection.execute(table.delete())


class SqlContractBackend:
    """Unités de travail SQL sur `engine`, vidé à la construction (une instance par test)."""

    def __init__(self, engine: sa.Engine) -> None:
        wipe(engine)
        self.engine = engine

    def uow(self, shop_id: ShopId, handlers: Sequence[EventHandler] = ()) -> SqlUnitOfWork:
        return SqlUnitOfWork(self.engine, shop_id, repositories=SQL_REGISTRY, handlers=handlers)

    def entitlement_overrides(self) -> EntitlementOverrides:
        return SqlEntitlementOverrides(self.engine)

    def platform_uow(
        self,
        handlers: Sequence[IdentityEventHandler] = (),
        shop_handlers: Sequence[EventHandler] = (),
    ) -> SqlIdentityUnitOfWork:
        return SqlIdentityUnitOfWork(
            self.engine, handlers, SqlShopJoin(SQL_REGISTRY, shop_handlers)
        )

    def memberships(self) -> MembershipDirectory:
        return SqlMembershipDirectory(self.engine)

    def catalog(self) -> ShopCatalog:
        return SqlShopCatalog(self.engine)

    def delegations(self) -> AdminDelegationDirectory:
        return SqlAdminDelegations(self.engine)
