"""UC-VEN-03 — Demandes de prix sous le minimum (ERR-PRM-05 à 09, E2E-06 côté serveur, Q-44)."""

from datetime import timedelta

import pytest

from app.application.audit.ports import AuditQuery
from app.application.sales.use_cases.price_requests import PriceRequestCommand
from app.application.security.actor import Actor
from app.application.security.errors import PermissionDenied
from app.domain.alerts.alert import AlertType
from app.domain.catalog.article import Article
from app.domain.catalog.prices import ArticlePrices
from app.domain.sales.errors import PriceBelowMinimum
from app.domain.sales.ids import PriceRequestId
from app.domain.sales.price_request import PriceRequestStatus
from app.domain.shared.errors import InvalidStateTransition, NotFound, ValidationFailed
from app.domain.shared.money import Money
from app.domain.shared.roles import Role
from tests.application.sales.support import SalesWorld
from tests.application.sales.test_record_sale import bought

type World = tuple[SalesWorld, Actor, Actor, Actor, Article]


def minimum_world() -> World:
    """HJ : base 780 000, minimum 720 000 (réglage actif, accord du propriétaire exigé)."""
    world, owner, accountant, seller, hj = bought()
    world.enable_min_price(owner)
    world.require_price_approval(owner)
    prices = ArticlePrices(base_price=Money(780_000), min_price=Money(720_000))
    world.catalog.prices.execute(owner, hj.id, prices, world.article(owner, hj).version)
    return world, owner, accountant, seller, world.article(owner, hj)


def ask(world: SalesWorld, seller: Actor, article: Article, price: int = 700_000) -> PriceRequestId:
    command = PriceRequestCommand(article_id=article.id, requested_price=price)
    view, created = world.sales.request_price.execute(seller, command)
    assert created
    assert view.status is PriceRequestStatus.PENDING
    return view.request.id


def sell(world: SalesWorld, seller: Actor, article: Article, price: int, request: PriceRequestId):  # type: ignore[no-untyped-def]
    line = world.line(article, price)
    return world.record(seller, line, price_request_id=request)[0]


def reason_of(world: SalesWorld, seller: Actor, article: Article, price: int, request) -> str:  # type: ignore[no-untyped-def]
    with pytest.raises(PriceBelowMinimum) as refused:
        sell(world, seller, article, price, request)
    return str(refused.value.details["price_request"])


def test_request_accept_sell_then_single_use() -> None:  # ERR-PRM-05, ERR-PRM-08
    world, owner, _, seller, hj = minimum_world()
    request = ask(world, seller, hj)
    alerts = [a for a in world.alerts(owner, owner) if a.type is AlertType.PRICE_REQUEST]
    assert len(alerts) == 1
    assert alerts[0].entity.type == "price_request"
    assert "minimum" in alerts[0].message
    assert [v.request.id for v in world.sales.list_price_requests.execute(owner)] == [request]
    assert reason_of(world, seller, hj, 700_000, request) == "pending"
    decided = world.sales.decide_price.execute(owner, request, accept=True, version=1)
    assert decided.status is PriceRequestStatus.ACCEPTED
    assert all(
        a.resolved_at is not None
        for a in world.alerts(owner, owner)
        if a.type is AlertType.PRICE_REQUEST
    )
    assert reason_of(world, seller, hj, 690_000, request) == "price_too_low"
    view = sell(world, seller, hj, 710_000, request)  # au moins le prix accordé
    linked = world.sales.get_price_request.execute(seller, request)
    assert linked.request.sale_id == view.sale.id
    assert reason_of(world, seller, hj, 710_000, request) == "used"
    assert world.sales.list_price_requests.execute(owner) == []
    mine = world.sales.list_price_requests.execute(seller)
    assert [v.request.id for v in mine] == [request]
    journal = world.journal(world.shop_of(owner), AuditQuery(modules={"sales"}))
    assert any(e.sensitive and "minimum" in e.summary for e in journal)
    assert any(e.sensitive and "acceptée" in e.summary for e in journal)


def test_refused_and_decided_twice() -> None:  # ERR-PRM-06
    world, owner, _, seller, hj = minimum_world()
    request = ask(world, seller, hj)
    world.sales.decide_price.execute(owner, request, accept=False)
    assert reason_of(world, seller, hj, 700_000, request) == "refused"
    with pytest.raises(InvalidStateTransition) as again:
        world.sales.decide_price.execute(owner, request, accept=True)
    assert again.value.details["status"] == "refused"
    with pytest.raises(PermissionDenied):
        world.sales.decide_price.execute(seller, request, accept=True)


def test_expiry_at_30_minutes_and_worker() -> None:  # ERR-PRM-07, ERR-PRM-09
    world, owner, _, seller, hj = minimum_world()
    pending = ask(world, seller, hj)
    accepted = ask(world, seller, hj, 705_000)
    world.clock.advance(timedelta(minutes=29, seconds=59))
    world.sales.decide_price.execute(owner, accepted, accept=True)  # valable 30 min dès l'accord
    world.clock.advance(timedelta(seconds=1))  # 30:00 pile : expirée
    with pytest.raises(InvalidStateTransition) as late:
        world.sales.decide_price.execute(owner, pending, accept=True)
    assert late.value.details["status"] == "expired"
    assert world.sales.get_price_request.execute(seller, pending).status.value == "expired"
    sell(world, seller, hj, 705_000, accepted)  # toujours valable
    third = ask(world, seller, hj)
    world.sales.decide_price.execute(owner, third, accept=True)
    world.clock.advance(timedelta(minutes=30))
    assert reason_of(world, seller, hj, 700_000, third) == "expired"
    expire = world.sales_module.expire_price_requests
    shop = world.shop_of(owner)
    assert expire.execute(shop, world.clock.now()) == 2  # la première et la troisième
    assert expire.execute(shop, world.clock.now()) == 0  # idempotent
    alerts = [a for a in world.alerts(owner, owner) if a.type is AlertType.PRICE_REQUEST]
    assert len(alerts) == 3
    assert all(a.resolved_at is not None for a in alerts)


def test_other_seller_other_article_and_owner_free() -> None:  # ERR-PRM-08
    world, owner, _, seller, hj = minimum_world()
    other = world.member(owner, "677000009", Role.SELLER, "Garoua")
    request = ask(world, seller, hj)
    world.sales.decide_price.execute(owner, request, accept=True)
    assert reason_of(world, other, hj, 700_000, request) == "other_seller"
    with pytest.raises(NotFound):
        world.sales.get_price_request.execute(other, request)
    sym = world.moto(owner, "Sym", "Sym", base_price=700_000)
    world.buy(owner, sym, 2, 500_000)
    prices = ArticlePrices(base_price=Money(700_000), min_price=Money(650_000))
    world.catalog.prices.execute(owner, sym.id, prices, world.article(owner, sym).version)
    assert reason_of(world, seller, world.article(owner, sym), 600_000, request) == "other_article"
    unknown = PriceRequestId.new()
    assert reason_of(world, seller, hj, 700_000, unknown) == "not_found"
    world.cash(owner, hj, 600_000)  # le propriétaire vend librement, sans demande


def test_request_checks_and_idempotence() -> None:
    world, owner, accountant, seller, hj = minimum_world()
    with pytest.raises(ValidationFailed):  # rien à demander au minimum ou au-dessus
        world.sales.request_price.execute(
            seller, PriceRequestCommand(article_id=hj.id, requested_price=720_000)
        )
    with pytest.raises(PermissionDenied):
        world.sales.request_price.execute(
            accountant, PriceRequestCommand(article_id=hj.id, requested_price=700_000)
        )
    rid = PriceRequestId.new()
    command = PriceRequestCommand(article_id=hj.id, requested_price=700_000, request_id=rid)
    assert world.sales.request_price.execute(seller, command)[1]
    view, created = world.sales.request_price.execute(seller, command)
    assert not created
    assert view.request.id == rid
    world.http.settings.update(
        owner, {"min_price_enabled": False}, world.http.settings.get(owner).version
    )
    with pytest.raises(ValidationFailed):  # réglage inactif : aucun minimum
        world.sales.request_price.execute(
            seller, PriceRequestCommand(article_id=hj.id, requested_price=1)
        )
