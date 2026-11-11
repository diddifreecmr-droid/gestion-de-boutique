"""Table et dépôts de test pour les garde-fous du gabarit SQL (hors contrat commun)."""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa

from app.application.ports.aggregate import UniqueKey
from app.application.ports.repository import Repository
from app.domain.shared.ids import ShopId
from app.infrastructure.persistence.sqlalchemy.repository import SqlRepository
from tests.contracts.backends.sql import test_metadata
from tests.contracts.widget import Widget, WidgetId

gadget_table = sa.Table(
    "gadget",
    test_metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("shop_id", sa.Uuid, nullable=False),
    sa.Column("label", sa.String(200), nullable=False),
    sa.Column("code", sa.String(50), nullable=True),
    sa.Column("version", sa.BigInteger, nullable=False),
    sa.CheckConstraint("label <> ''", name="label_not_empty"),
    sa.Index("gadget_code", "shop_id", "code", unique=True),  # unicité par index nommé
    sa.Index("gadget_label_first", "label", "shop_id", unique=True),
)


class GadgetRepository(Repository[WidgetId, Widget]):
    """Port de test : `code` unique par boutique, porté par un index UNIQUE."""

    def unique_keys(self) -> Sequence[UniqueKey[Widget]]:
        return (UniqueKey("gadget_code", lambda gadget: gadget.code),)


class SqlGadgetRepository(SqlRepository[WidgetId, Widget], GadgetRepository):
    table = gadget_table

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
