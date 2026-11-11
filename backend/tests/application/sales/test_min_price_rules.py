"""Prix minimum (H9, UC-VEN-03 ; décision client specs § 15.1) : avertissement par défaut, accord
du propriétaire seulement si le réglage `min_price_requires_approval` est vrai (ERR-PRM-01 à 03).
"""

import pytest

from app.application.audit.ports import AuditQuery
from app.application.sales.use_cases.price_requests import PriceRequestCommand
from app.application.security.actor import Actor
from app.domain.catalog.article import Article
from app.domain.catalog.prices import ArticlePrices
from app.domain.sales.errors import PriceApprovalDisabled, PriceBelowMinimum
from app.domain.shared.money import Money
from tests.application.sales.support import SalesWorld
from tests.application.sales.test_record_sale import bought


def minimum_world() -> tuple[SalesWorld, Actor, Actor, Article]:
    """HJ : base 780 000, minimum 720 000, prix minimum actif ; accord **non** exigé (défaut)."""
    world, owner, _, seller, hj = bought()
    world.enable_min_price(owner)
    prices = ArticlePrices(base_price=Money(780_000), min_price=Money(720_000))
    world.catalog.prices.execute(owner, hj.id, prices, world.article(owner, hj).version)
    return world, owner, seller, world.article(owner, hj)


def sensitive_sales(world: SalesWorld, owner: Actor) -> list[bool]:
    journal = world.journal(world.shop_of(owner), AuditQuery(modules={"sales"}))
    return [e.sensitive for e in journal if "minimum" in e.summary]


def test_default_setting_is_off() -> None:
    world, owner, _, _ = minimum_world()
    assert world.http.settings.get(owner).values.min_price_requires_approval is False


def test_seller_below_minimum_is_accepted_with_a_warning() -> None:
    world, owner, seller, hj = minimum_world()
    view = world.cash(seller, hj, 700_000)
    [warning] = view.warnings
    assert warning.code == "PRICE_BELOW_MINIMUM"
    assert warning.message == "Prix inférieur au minimum de 720 000 FCFA"
    assert warning.details == {"article_id": str(hj.id), "line": 1, "min_price": 720_000}
    assert world.cash(seller, hj, 720_000).warnings == ()  # « en dessous » est strict
    assert world.cash(owner, hj, 600_000).warnings == ()
    assert sensitive_sales(world, owner) == [True, True]  # journal : action sensible


def test_two_lines_below_give_two_warnings() -> None:
    world, _, seller, hj = minimum_world()
    view, _ = world.record(seller, world.line(hj, 700_000), world.line(hj, 710_000))
    assert [w.details["line"] for w in view.warnings] == [1, 2]


def test_price_request_refused_when_approval_is_not_required() -> None:
    world, _, seller, hj = minimum_world()
    command = PriceRequestCommand(article_id=hj.id, requested_price=700_000)
    with pytest.raises(PriceApprovalDisabled) as refused:
        world.sales.request_price.execute(seller, command)
    assert refused.value.code == "PRICE_APPROVAL_DISABLED"


def test_approval_required_seller_refused_owner_accepted() -> None:
    world, owner, seller, hj = minimum_world()
    world.require_price_approval(owner)
    with pytest.raises(PriceBelowMinimum) as refused:  # ERR-PRM-01
        world.cash(seller, hj, 719_999)
    assert refused.value.details == {
        "article_id": str(hj.id),
        "line": 1,
        "min_price": 720_000,
        "request_required": True,
    }
    world.cash(seller, hj, 720_000)  # ERR-PRM-02 : « en dessous » est strict
    assert world.cash(owner, hj, 600_000).warnings == ()  # ERR-PRM-03
    assert sensitive_sales(world, owner) == [True]


def test_setting_change_is_journaled() -> None:
    world, owner, _, _ = minimum_world()
    world.require_price_approval(owner)
    journal = world.journal(world.shop_of(owner))
    [entry] = [e for e in journal if "min_price_requires_approval" in e.summary]
    assert [(c.field, c.before, c.after) for c in entry.changes] == [
        ("min_price_requires_approval", False, True)
    ]
