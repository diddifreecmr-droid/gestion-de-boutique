"""Gabarit de dépôt SQL : déclaration de table, d'unicité et de colonnes vérifiées tôt."""

from collections.abc import Sequence
from typing import Any

import pytest
import sqlalchemy as sa

from app.application.ports.aggregate import UniqueKey
from app.domain.shared.errors import Duplicate
from app.domain.shared.ids import ShopId
from app.infrastructure.persistence.sqlalchemy.uow import SqlUnitOfWork
from tests.contracts.backends.sql import SqlContractBackend, SqlWidgetRepository
from tests.contracts.widget import Widget, WidgetId, WidgetRepository
from tests.infrastructure.sqlalchemy.gadget import GadgetRepository, SqlGadgetRepository

SHOP = ShopId.new()


def uow_with(backend: SqlContractBackend, *adapters: type[Any]) -> SqlUnitOfWork:
    return SqlUnitOfWork(backend.engine, SHOP, repositories=adapters)


class NoTable(SqlWidgetRepository):
    table = None  # type: ignore[assignment]  # oubli simulé


class MissingVersion(SqlWidgetRepository):
    table = sa.Table("sans_version", sa.MetaData(), sa.Column("id", sa.Uuid, primary_key=True))


class UndeclaredKey(SqlWidgetRepository):
    def unique_keys(self) -> Sequence[UniqueKey[Widget]]:
        return (UniqueKey("absente", lambda widget: widget.code),)


class KeyNotScopedToShop(SqlGadgetRepository):
    def unique_keys(self) -> Sequence[UniqueKey[Widget]]:
        return (UniqueKey("gadget_label_first", lambda gadget: gadget.label),)


class LeaksIdentity(SqlWidgetRepository):
    def _to_columns(self, aggregate: Widget) -> dict[str, Any]:
        return {"label": aggregate.label, "version": 99}


@pytest.mark.parametrize(
    ("adapter", "message"),
    [
        (NoTable, "table"),
        (MissingVersion, "colonnes obligatoires"),
        (UndeclaredKey, "sans contrainte UNIQUE"),
        (KeyNotScopedToShop, "commencer par shop_id"),
    ],
)
def test_bad_declarations_fail_at_construction(
    backend: SqlContractBackend, adapter: type[Any], message: str
) -> None:
    port = GadgetRepository if issubclass(adapter, SqlGadgetRepository) else WidgetRepository
    with uow_with(backend, adapter) as uow, pytest.raises(TypeError, match=message):
        port.within(uow)


def test_to_columns_cannot_override_identity(backend: SqlContractBackend) -> None:
    with uow_with(backend, LeaksIdentity) as uow, pytest.raises(ValueError, match="version"):
        WidgetRepository.within(uow).add(Widget.create(SHOP, "x"))


def test_unique_index_is_translated_to_duplicate(backend: SqlContractBackend) -> None:
    with uow_with(backend, SqlGadgetRepository) as uow:
        gadgets = GadgetRepository.within(uow)
        gadgets.add(Widget.create(SHOP, "a", code="G-1"))
        with pytest.raises(Duplicate) as caught:
            gadgets.add(Widget.create(SHOP, "b", code="G-1"))
        assert caught.value.details == {"table": "gadget", "constraint": "gadget_code"}
        gadgets.add(Widget.create(SHOP, "c", code="G-2"))  # la transaction reste utilisable
        uow.commit()


def test_integrity_error_that_is_not_a_duplicate_is_reraised(
    backend: SqlContractBackend,
) -> None:
    with uow_with(backend, SqlGadgetRepository) as uow:
        gadgets = GadgetRepository.within(uow)
        with pytest.raises(sa.exc.IntegrityError, match=r"label_not_empty|CHECK"):
            gadgets.add(Widget.create(SHOP, ""))
        stored = Widget.create(SHOP, "ok")
        gadgets.add(stored)
        stored.label = ""
        with pytest.raises(sa.exc.IntegrityError):
            gadgets.update(stored)
        assert stored.version == 1
        uow.rollback()


def test_unregistered_port_is_a_lookup_error(backend: SqlContractBackend) -> None:
    with uow_with(backend) as uow, pytest.raises(LookupError, match="adaptateur SQL"):
        WidgetRepository.within(uow)


def test_widget_id_round_trips(backend: SqlContractBackend) -> None:
    widget = Widget.create(SHOP, "aller-retour", code="R")
    with uow_with(backend, SqlWidgetRepository) as uow:
        WidgetRepository.within(uow).add(widget)
        uow.commit()
    with uow_with(backend, SqlWidgetRepository) as uow:
        loaded = WidgetRepository.within(uow).get(widget.id)
    assert isinstance(loaded.id, WidgetId)
    assert (loaded.id, loaded.shop_id) == (widget.id, SHOP)
