"""Textile vendu au mètre et à la pièce (RG-X02, arrondi T04), modes refusés, détails hors
profil ; réessai borné sur course de concurrence (`with_sale_retry`)."""

import pytest

from app.application.catalog.use_cases.context import ArticleInput
from app.application.catalog.use_cases.create_article import CreateArticleCommand
from app.application.sales.inputs import LineInput, SaleInput
from app.application.sales.retry import is_sale_race, with_sale_retry
from app.application.sales.use_cases.record_sale import RecordSaleCommand
from app.domain.catalog.prices import ArticlePrices
from app.domain.sales.errors import ChassisAlreadySold
from app.domain.sales.lines import SaleMode, SoldDetail
from app.domain.sales.values import SaleKind
from app.domain.shared.errors import Duplicate, ValidationFailed, VersionConflict
from app.domain.shared.money import Money
from tests.application.sales.support import SalesWorld


def test_textile_meter_and_piece_lines() -> None:
    world = SalesWorld()
    owner = world.open_profile("textile")
    fields = {"name": "Wax Fleur", "unit": "METER", "sold_by_piece": True, "piece_length_m": "5.49"}
    prices = ArticlePrices(base_price=Money(2_500), base_price_piece=Money(13_000))
    command = CreateArticleCommand(data=ArticleInput(fields=fields), prices=prices)
    wax, _ = world.catalog.create.execute(owner, command)
    world.stock_in(owner, wax, "Boutique", "50")

    def sell(*lines: LineInput) -> SaleInput:
        return SaleInput(kind=SaleKind.CASH, lines=lines, payments=())

    meter = LineInput(article_id=wax.id, quantity="2.5", unit_price=0)
    piece = LineInput(article_id=wax.id, quantity=2, unit_price=0, sale_mode=SaleMode.PIECE)
    view, _ = world.sales.record.execute(owner, RecordSaleCommand(data=sell(meter, piece)))
    first, second = view.sale.content.lines
    assert (first.sale_mode, str(first.stock_quantity), first.base_price) == (
        SaleMode.METER,
        "2.5",
        Money(2_500),
    )
    assert (str(second.stock_quantity), second.base_price) == ("11.0", Money(13_000))
    assert world.matrix_total(owner, wax) == "36.5"
    unit = LineInput(article_id=wax.id, quantity=1, unit_price=0, sale_mode=SaleMode.UNIT)
    colored = LineInput(
        article_id=wax.id, quantity=1, unit_price=0, details=(SoldDetail(color="Rouge"),)
    )
    for refused in (unit, colored):
        with pytest.raises(ValidationFailed):
            world.sales.record.execute(owner, RecordSaleCommand(data=sell(refused)))


def test_sale_retry_replays_races_only() -> None:
    attempts: list[int] = []

    def racing() -> str:
        attempts.append(1)
        if len(attempts) < 2:
            raise Duplicate("course", details={"constraint": "sold_chassis_active"})
        return "ok"

    assert with_sale_retry(racing) == "ok"
    assert len(attempts) == 2
    assert not is_sale_race(ChassisAlreadySold("LBX1", "V-000001"))
    assert is_sale_race(VersionConflict("conflit"))

    def always() -> str:
        raise VersionConflict("conflit")

    with pytest.raises(VersionConflict):
        with_sale_retry(always)
    with pytest.raises(ValueError, match="au moins"):
        with_sale_retry(always, attempts=0)
