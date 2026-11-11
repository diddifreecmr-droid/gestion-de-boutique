"""Agrégat `Alert` (lue, résolue, clé active) et droits d'offre."""

from datetime import UTC, datetime

import pytest

from app.domain.alerts.alert import Alert, AlertType
from app.domain.audit.values import EntityRef
from app.domain.plans.entitlements import Entitlement, PlanCode, plan_grants
from app.domain.shared.ids import ShopId, UserId

NOW = datetime(2026, 11, 10, 8, 0, tzinfo=UTC)
TARGET = EntityRef("article", UserId.new().value)


def alert(**overrides: object) -> Alert:
    values: dict[str, object] = {
        "shop_id": ShopId.new(),
        "recipient_id": UserId.new(),
        "type": AlertType.LOW_STOCK,
        "entity": TARGET,
        "message": "Stock bas",
        "now": NOW,
        "dedup_key": "low_stock:a",
    }
    return Alert.raise_for(**(values | overrides))  # type: ignore[arg-type]


def test_twelve_cdc_types() -> None:
    assert len(AlertType) == 12


def test_read_and_resolve_lifecycle() -> None:
    made = alert()
    assert (made.read, made.active, made.dedup_active_key) == (False, True, "low_stock:a")
    assert made.mark_read() is True
    assert made.mark_read() is False
    made.resolve(NOW)
    made.resolve(datetime(2027, 1, 1, tzinfo=UTC))  # sans effet : déjà résolue
    assert (made.active, made.dedup_active_key, made.resolved_at) == (False, None, NOW)


@pytest.mark.parametrize(
    "overrides",
    [
        {"recipient_id": "u"},
        {"type": "low_stock"},
        {"entity": EntityRef("article")},
        {"message": ""},
        {"dedup_key": " "},
        {"dedup_key": "k" * 201},
    ],
)
def test_invalid_alerts_are_refused(overrides: dict[str, object]) -> None:
    with pytest.raises((TypeError, ValueError)):
        alert(**overrides)


def test_free_plan_grants_no_premium_entitlement() -> None:
    assert plan_grants(PlanCode.FREE, Entitlement.OFFLINE_CAPTURE) is False
    with pytest.raises(TypeError):
        plan_grants(PlanCode.FREE, "offline_capture")  # type: ignore[arg-type]
