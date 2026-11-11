"""Valeurs et entrée du journal : validation stricte, immuabilité, pastille sensible."""

import dataclasses
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest

from app.domain.audit.entry import AuditEntry, AuditEntryId, AuditRecord
from app.domain.audit.values import AuditAction, EntityRef, FieldChange, Performer
from app.domain.shared.ids import DeviceId, ShopId, UserId

FLOAT: Any = 1.5
NOW = datetime(2026, 11, 10, 13, 32, tzinfo=UTC)
WHO = Performer(UserId.new(), "seller", DeviceId.new())


def record(**overrides: object) -> AuditRecord:
    values: dict[str, object] = {
        "performer": WHO,
        "action": AuditAction.CREATE,
        "entity": EntityRef("sale", None, "V-000124"),
        "module": "sales",
        "summary": "Vente V-000124",
    }
    return AuditRecord(**(values | overrides))  # type: ignore[arg-type]


def test_every_cdc_action_has_a_french_label() -> None:
    assert len(AuditAction) == 11
    assert AuditAction.CONFIGURE.label == "Régler"
    assert AuditAction.ACCESS_DENIED.label == "Accès refusé"


@pytest.mark.parametrize(
    "build",
    [
        lambda: EntityRef("Vente"),
        lambda: EntityRef("sale", "pas-un-uuid"),  # type: ignore[arg-type]
        lambda: EntityRef("sale", number=" "),
        lambda: FieldChange("price", FLOAT, 2),
        lambda: Performer("u", "seller"),  # type: ignore[arg-type]
        lambda: Performer(UserId.new(), "seller", "d"),  # type: ignore[arg-type]
        lambda: record(performer="x"),
        lambda: record(action="create"),
        lambda: record(module="Ventes"),
        lambda: record(summary=""),
        lambda: record(reason="x" * 501),
        lambda: record(changes=["price"]),
        lambda: record(captured_at=datetime(2026, 11, 10)),
        lambda: AuditEntry(**cast(Any, {**vars_of(entry()), "id": UserId.new()})),
    ],
)
def test_invalid_values_are_refused(build: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        build()  # type: ignore[operator]


def entry(**overrides: object) -> AuditEntry:
    return AuditEntry.inscribe(
        ShopId.new(), record(**overrides), received_at=NOW, default_captured_at=NOW
    )


def vars_of(item: AuditEntry) -> dict[str, object]:
    return {f.name: getattr(item, f.name) for f in dataclasses.fields(item)}


def test_entry_is_frozen() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        entry().summary = "réécrit"  # type: ignore[misc]


def test_sensitivity_rules() -> None:
    assert not entry().sensitive
    assert entry(sensitive=True).sensitive
    assert entry(action=AuditAction.CANCEL).sensitive
    late = entry(captured_at=NOW - timedelta(minutes=16))
    assert late.sensitive
    assert late.captured_at < late.received_at
    assert not entry(captured_at=NOW - timedelta(minutes=15)).sensitive


def test_explicit_id_is_kept() -> None:
    ident = AuditEntryId.new()
    made = AuditEntry.inscribe(
        ShopId.new(), record(), received_at=NOW, default_captured_at=NOW, entry_id=ident
    )
    assert made.id == ident
