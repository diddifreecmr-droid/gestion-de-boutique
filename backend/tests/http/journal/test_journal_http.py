"""`/shops/{id}/audit*` et `/shops/{id}/alerts*` (AUD-01, AUD-03, AUD-04, ALR-01, ALR-03, M27)."""

from app.application.alerts.ports import AlertRepository
from app.application.security.roles import Role
from app.domain.alerts.alert import Alert, AlertType
from app.domain.audit.values import EntityRef
from app.domain.shared.ids import UserId
from tests.application.identity.support import T0
from tests.http.journal.conftest import Shop


def test_seller_is_refused_the_journal_and_the_refusal_is_journaled(shop: Shop) -> None:
    owner = shop.member("677000001", Role.OWNER)
    seller = shop.member("677000002", Role.SELLER)
    for path in (
        "/audit",
        f"/audit/users/{owner.user.id}",
        f"/audit/entities/sale/{owner.user.id}",
    ):
        refused = shop.call("GET", path, seller)
        assert refused.status_code == 403
        assert refused.json()["error"]["code"] == "FORBIDDEN"
    listing = shop.call("GET", "/audit", owner, action="access_denied", limit=2)
    assert listing.status_code == 200
    body = listing.json()
    assert len(body["items"]) == 2
    assert body["next_cursor"] is not None
    first = body["items"][0]
    assert first["performer"] == {
        "user_id": str(seller.user.id),
        "role": "seller",
        "device_id": str(seller.device),
    }
    assert (first["action_label"], first["entity"]["number"]) == ("Accès refusé", "AUDIT_READ")
    rest = shop.call("GET", "/audit", owner, cursor=body["next_cursor"]).json()
    assert len(rest["items"]) == 1
    assert rest["next_cursor"] is None


def test_owner_filters_by_user_period_and_entity(shop: Shop) -> None:
    owner = shop.member("677000001", Role.OWNER)
    seller = shop.member("677000002", Role.SELLER)
    shop.call("GET", "/audit", seller)
    activity = shop.call("GET", f"/audit/users/{seller.user.id}", owner).json()
    assert [i["action"] for i in activity["items"]] == ["access_denied"]
    today = T0.date().isoformat()
    period = shop.call("GET", "/audit", owner, **{"from": today, "to": today}).json()
    assert len(period["items"]) == 1
    yesterday = shop.call("GET", "/audit", owner, **{"from": "2026-11-01"}).json()
    assert yesterday["items"] == []
    history = shop.call("GET", f"/audit/entities/sale/{seller.user.id}", owner).json()
    assert history == {"items": [], "next_cursor": None}
    assert shop.call("GET", "/audit", owner, module="security").json()["items"]


def test_bad_cursor_and_bad_ids_are_400(shop: Shop) -> None:
    owner = shop.member("677000001", Role.OWNER)
    assert shop.call("GET", "/audit", owner, cursor="%%%").status_code == 400
    assert shop.call("GET", "/audit", owner, user_id="pas-un-id").status_code == 400
    assert shop.call("GET", "/audit/entities/sale/xyz", owner).status_code == 400


def raise_alert(shop: Shop, recipient: UserId) -> Alert:
    alert = Alert.raise_for(
        shop_id=shop.shop_id,
        recipient_id=recipient,
        type=AlertType.SALE_ERROR_REPORTED,
        entity=EntityRef("sale", shop.shop_id.value, "V-000124"),
        message="Erreur signalée sur V-000124",
        now=T0,
    )
    with shop.journal.uow_factory(shop.shop_id) as uow:
        AlertRepository.within(uow).add(alert)
        uow.commit()
    return alert


def test_each_user_sees_and_reads_only_their_alerts(shop: Shop) -> None:
    owner = shop.member("677000001", Role.OWNER)
    seller = shop.member("677000002", Role.SELLER)
    alert = raise_alert(shop, owner.user.id)
    mine = shop.call("GET", "/alerts", owner).json()
    assert mine["unread_count"] == 1
    assert mine["items"][0]["entity"]["number"] == "V-000124"
    assert shop.call("GET", "/alerts", seller).json() == {
        "items": [],
        "next_cursor": None,
        "unread_count": 0,
    }
    stolen = shop.call("POST", f"/alerts/{alert.id}/read", seller)
    assert stolen.status_code == 404
    read = shop.call("POST", f"/alerts/{alert.id}/read", owner)
    assert read.json() == {"unread_count": 0}
    assert shop.call("POST", f"/alerts/{alert.id}/read", owner).json() == {"unread_count": 0}
    assert shop.call("GET", "/alerts", owner, unread_only=True).json()["items"] == []
