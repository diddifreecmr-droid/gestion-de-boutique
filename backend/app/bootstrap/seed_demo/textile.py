"""« Démo Tissus » : dix tissus créés par `CreateFabric` (un article par couleur).

Rouleaux de 25 m ou 30 m ; stock initial saisi **en rouleaux** (Djampar rouge 7 rouleaux,
Satin noir 50 rouleaux) ; ventes au mètre et au rouleau. Getzner est vendu au mètre seulement :
son stock est saisi en mètres.
"""

from decimal import Decimal
from typing import NamedTuple

from app.application.catalog.fabrics import FabricTerms
from app.application.catalog.use_cases.create_fabric import CreateFabricCommand
from app.application.security.actor import Actor
from app.bootstrap.seed_demo.plan import Expense, ShopPlan, StockedItem, options, staff
from app.domain.catalog.fabric import FabricShape
from app.domain.catalog.ids import ArticleId
from app.domain.catalog.prices import ArticlePrices
from app.domain.profiles.profile import ProfileCode
from app.domain.purchasing.units import EntryUnit
from app.domain.sales.lines import SaleMode
from app.domain.shared.money import Money
from app.interface.http.routes.catalog import CatalogComponents


class Fabric(NamedTuple):
    name: str
    roll: int | None
    meter_price: int
    roll_price: int | None
    cost: int
    colors: dict[str, int]


FABRICS = tuple(
    Fabric(*row)
    for row in (
        ("Tergal", 30, 1_500, 42_000, 33_000, {"Noir": 6, "Bleu marine": 5, "Gris": 4}),
        ("Gabardine", 25, 2_000, 47_000, 37_500, {"Beige": 5, "Noir": 4}),
        ("Popline lourd", 30, 1_200, 33_000, 25_500, {"Blanc": 8, "Bleu ciel": 4, "Kaki": 3}),
        ("Popline léger", 30, 900, 25_000, 19_000, {"Blanc": 6, "Rose": 3}),
        ("Getzner", None, 12_000, None, 8_500, {"Blanc": 120, "Bleu roi": 80, "Bordeaux": 60}),
        ("Superfine 360's", 25, 3_500, 82_000, 65_000, {"Noir": 4, "Bleu nuit": 3, "Gris": 2}),
        ("Satin", 25, 1_000, 23_000, 17_500, {"Noir": 50, "Blanc": 10, "Rouge": 8, "Doré": 6}),
        ("Toyobo simple", 30, 1_800, 50_000, 39_000, {"Blanc": 5, "Crème": 4}),
        ("Toyobo carelle", 30, 2_200, 61_000, 47_000, {"Bleu": 4, "Vert": 3, "Marron": 3}),
        ("Djampar", 25, 1_600, 37_000, 29_000, {"Rouge": 7, "Jaune": 5, "Vert": 4}),
    )
)
"""(tissu, longueur du rouleau en m ou `None` (au mètre seulement), prix au mètre, prix du
rouleau, coût d'achat (par rouleau ; par mètre si au mètre seulement), stock initial par
couleur (rouleaux ; mètres si au mètre seulement))."""


def _item(article_id: ArticleId, fabric: Fabric, opening: int) -> StockedItem:
    meter_price, roll_price, cost = fabric.meter_price, fabric.roll_price, fabric.cost
    if roll_price is None:
        return StockedItem(
            article_id=article_id,
            opening=Decimal(opening),
            unit_cost=cost,
            sales=options((3, meter_price, SaleMode.METER), (2, meter_price, SaleMode.METER)),
            entry_unit=EntryUnit.METER,
            restock=Decimal(30),
        )
    return StockedItem(
        article_id=article_id,
        opening=Decimal(opening),
        unit_cost=cost,
        sales=options((3, meter_price, SaleMode.METER), (1, roll_price, SaleMode.PIECE)),
        entry_unit=EntryUnit.PIECE,
    )


def build_textile(catalog: CatalogComponents, owner: Actor) -> list[StockedItem]:
    items = []
    for fabric in FABRICS:
        roll, colors = fabric.roll, fabric.colors
        prices = ArticlePrices(
            base_price=Money(fabric.meter_price),
            base_price_piece=None if fabric.roll_price is None else Money(fabric.roll_price),
        )
        shape = FabricShape(
            roll_length_m=None if roll is None else Decimal(roll), meter_only=roll is None
        )
        command = CreateFabricCommand(
            fabric=fabric.name, colors=tuple(colors), terms=FabricTerms(shape=shape, prices=prices)
        )
        view = catalog.fabrics.create.execute(owner, command)
        for article in view.articles:
            opening = colors[str(article.details.fields.attributes.get("color", ""))]
            items.append(_item(article.id, fabric, opening))
    return items


_PEOPLE = staff(
    3,
    ("Gérant", "Employée", "Employé", "Comptable"),
    ("Mamadou Oumarou", "Hadjara Aminatou", "Christian Mbida", "Florence Ateba"),
)

TEXTILE_PLAN = ShopPlan(
    profile=ProfileCode.TEXTILE,
    name="Démo Tissus",
    city="Yaoundé",
    phone="690001300",
    owner=_PEOPLE[0],
    sellers=(_PEOPLE[1], _PEOPLE[2]),
    accountant=_PEOPLE[3],
    suppliers=("Tissus Mokolo Gros", "Import Lagos Textiles", "Getzner Afrique (Douala)"),
    expenses=(
        Expense("Autre", 15_000, "Sacs et papier d'emballage", 5),
        Expense("Salaire", 60_000, "Avance sur salaire (employée)", 2),
    ),
    catalog=build_textile,
    customer=("Tailleur Abdou Couture", "677451232"),
)
