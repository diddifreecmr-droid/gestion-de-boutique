"""T29 — Droits et délai de l'échange (UC-PAP-01, décision client QC-4 ; EXC-L3-03/04,
AUD-L3-01) : réglage `employee_exchange_allowed` faux par défaut, vendeur sur **ses** ventes et
dans le délai `exchange_days`, propriétaire toujours (hors délai = journal sensible)."""

from datetime import timedelta
from typing import Any

import pytest

from app.application.audit.ports import AuditQuery
from app.application.sales.exchange_rights import EmployeeExchangeDisabled
from app.application.sales.inputs import SaleInput
from app.application.sales.returning import ReturnLineInput
from app.application.sales.use_cases.record_return import ExchangeInput, ReturnCommand
from app.application.security.actor import Actor
from app.application.security.errors import PermissionDenied
from app.domain.catalog.article import Article
from app.domain.sales.exchange_period import ExchangePeriodOver
from app.domain.sales.ids import SaleId, SaleReturnId
from app.domain.sales.values import SaleKind
from app.domain.shared.errors import NotFound
from tests.application.sales.support import SalesWorld
from tests.application.sales.test_exchanges import sym
from tests.application.sales.test_record_sale import bought

type Setup = tuple[SalesWorld, Actor, Actor, Actor, Article, Article]


def configure(world: SalesWorld, owner: Actor, **values: Any) -> None:
    version = world.http.settings.get(owner).version
    world.http.settings.update(owner, values, version)


def world_with(**values: Any) -> Setup:
    world, owner, accountant, seller, hj = bought()
    other = sym(world, owner)
    if values:
        configure(world, owner, **values)
    return world, owner, accountant, seller, hj, other


def command(
    world: SalesWorld, actor: Actor, sale_id: SaleId, new: Article, price: int, **extra: Any
) -> ReturnCommand:
    data = SaleInput(kind=SaleKind.CASH, lines=(world.line(new, price),))
    return ReturnCommand(
        sale_id=sale_id,
        lines=(ReturnLineInput(line=1, quantity=1),),
        reason="autre modèle",
        exchange=ExchangeInput(sale=data, mode_id=world.mode(actor)),
        **extra,
    )


def late_entries(world: SalesWorld, owner: Actor) -> list[bool]:
    journal = world.journal(world.shop_of(owner), AuditQuery(modules={"sales"}))
    return [e.sensitive for e in journal if "hors délai" in e.summary]


def test_setting_is_off_by_default_and_journaled() -> None:
    world, owner, *_ = world_with()
    assert world.http.settings.get(owner).values.employee_exchange_allowed is False
    configure(world, owner, employee_exchange_allowed=True)
    [entry] = [e for e in world.journal(world.shop_of(owner)) if "employee_exch" in e.summary]
    assert [(c.field, c.before, c.after) for c in entry.changes] == [
        ("employee_exchange_allowed", False, True)
    ]


def test_seller_cannot_change_the_setting() -> None:
    world, _, _, seller, *_ = world_with()
    with pytest.raises(PermissionDenied):
        world.http.settings.update(seller, {"employee_exchange_allowed": True}, 1)


def test_seller_refused_while_setting_is_off() -> None:  # EXC-L3-04
    world, _, _, seller, hj, other = world_with()
    sold = world.cash(seller, hj, 780_000).sale
    with pytest.raises(EmployeeExchangeDisabled) as raised:
        world.sales.record_return.execute(seller, command(world, seller, sold.id, other, 780_000))
    assert raised.value.details["setting"] == "employee_exchange_allowed"
    assert world.matrix_total(seller, hj) == "19"  # rien n'a bougé


def test_seller_exchanges_own_sale_when_allowed() -> None:  # EXC-L3-04
    world, owner, _, seller, hj, other = world_with(employee_exchange_allowed=True)
    sold = world.cash(seller, hj, 780_000).sale
    view, created = world.sales.record_return.execute(
        seller, command(world, seller, sold.id, other, 780_000)
    )
    assert created
    assert view.exchange is not None
    assert view.exchange.sale.seller_id == seller.user_id
    assert late_entries(world, owner) == []


def test_seller_cannot_exchange_someone_elses_sale() -> None:  # EXC-L3-04 : 404
    world, owner, _, seller, hj, other = world_with(employee_exchange_allowed=True)
    sold = world.cash(owner, hj, 780_000).sale
    with pytest.raises(NotFound):
        world.sales.record_return.execute(seller, command(world, seller, sold.id, other, 780_000))


def test_simple_return_stays_owner_only() -> None:
    world, _, accountant, seller, hj, _ = world_with(employee_exchange_allowed=True)
    sold = world.cash(seller, hj, 780_000).sale
    plain = ReturnCommand(
        sale_id=sold.id, lines=(ReturnLineInput(line=1, quantity=1),), reason="défaut"
    )
    with pytest.raises(PermissionDenied):
        world.sales.record_return.execute(seller, plain)
    with pytest.raises(PermissionDenied):
        world.sales.record_return.execute(accountant, command(world, seller, sold.id, hj, 1))


@pytest.mark.parametrize(("days_after", "late"), [(3, False), (7, False), (8, True)])
def test_period_for_the_seller(days_after: int, *, late: bool) -> None:  # EXC-L3-03
    world, _, _, seller, hj, other = world_with(employee_exchange_allowed=True, exchange_days=7)
    sold = world.cash(seller, hj, 780_000).sale
    world.clock.advance(timedelta(days=days_after))
    wanted = command(world, seller, sold.id, other, 780_000)
    if not late:
        assert world.sales.record_return.execute(seller, wanted)[1]
        return
    with pytest.raises(ExchangePeriodOver) as raised:
        world.sales.record_return.execute(seller, wanted)
    assert raised.value.code == "EXCHANGE_PERIOD_OVER"
    assert raised.value.details["exchange_days"] == 7
    assert raised.value.details["sold_on"] == sold.content.sold_on.isoformat()


def test_owner_exceeds_the_period_with_a_sensitive_entry() -> None:  # EXC-L3-03, AUD-L3-01
    world, owner, _, seller, hj, other = world_with(exchange_days=7)
    sold = world.cash(seller, hj, 780_000).sale
    world.clock.advance(timedelta(days=8))
    view, created = world.sales.record_return.execute(
        owner, command(world, owner, sold.id, other, 780_000)
    )
    assert created
    assert view.exchange is not None
    assert late_entries(world, owner) == [True]


def test_owner_within_period_is_not_sensitive() -> None:
    world, owner, _, seller, hj, other = world_with(exchange_days=7)
    sold = world.cash(seller, hj, 780_000).sale
    world.sales.record_return.execute(owner, command(world, owner, sold.id, other, 780_000))
    assert late_entries(world, owner) == []


def test_replay_after_the_period_stays_idempotent() -> None:
    world, _, _, seller, hj, other = world_with(employee_exchange_allowed=True, exchange_days=7)
    sold = world.cash(seller, hj, 780_000).sale
    wanted = command(world, seller, sold.id, other, 780_000, return_id=SaleReturnId.new())
    assert world.sales.record_return.execute(seller, wanted)[1]
    world.clock.advance(timedelta(days=30))
    assert world.sales.record_return.execute(seller, wanted)[1] is False


def test_seller_replay_of_another_sales_return_is_not_found() -> None:
    world, owner, _, seller, hj, other = world_with(employee_exchange_allowed=True)
    mine = world.cash(seller, hj, 780_000).sale
    theirs = world.cash(owner, hj, 780_000).sale
    rid = SaleReturnId.new()
    world.sales.record_return.execute(
        owner, command(world, owner, theirs.id, other, 780_000, return_id=rid)
    )
    with pytest.raises(NotFound):
        world.sales.record_return.execute(
            seller, command(world, seller, mine.id, other, 780_000, return_id=rid)
        )
