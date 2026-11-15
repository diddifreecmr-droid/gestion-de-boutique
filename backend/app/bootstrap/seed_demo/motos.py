"""« Démo Motos » : huit modèles de motos, vendus à l'unité.

Décision du client : **aucun** numéro de châssis ni de moteur n'est saisi dans les ventes de
démonstration (champs facultatifs du profil Motos).
"""

from decimal import Decimal

from app.application.catalog.use_cases.context import ArticleInput
from app.application.catalog.use_cases.create_article import CreateArticleCommand
from app.application.security.actor import Actor
from app.bootstrap.seed_demo.plan import Expense, ShopPlan, StockedItem, options, staff
from app.domain.catalog.prices import ArticlePrices
from app.domain.profiles.profile import ProfileCode
from app.domain.shared.money import Money
from app.interface.http.routes.catalog import CatalogComponents

MOTOS = (
    ("Haojue", "HJ125-8", 125, 780_000, 600_000, 5),
    ("Haojue", "DK150", 150, 950_000, 730_000, 3),
    ("Bajaj", "Boxer BM150", 150, 850_000, 650_000, 4),
    ("Bajaj", "Boxer BM100", 100, 720_000, 550_000, 3),
    ("TVS", "HLX 125", 125, 690_000, 520_000, 4),
    ("Sanili", "SL125-7", 125, 620_000, 470_000, 6),
    ("Nanfang", "NF125-2", 125, 600_000, 455_000, 3),
    ("Yamaha", "Crux 110", 110, 890_000, 700_000, 2),
)
"""(marque, modèle, cylindrée en cm³, prix de vente, coût d'achat, stock initial)."""


def build_motos(catalog: CatalogComponents, owner: Actor) -> list[StockedItem]:
    items = []
    for brand, model, engine_cc, price, cost, opening in MOTOS:
        fields = {"brand": brand, "model": model, "engine_cc": engine_cc, "category": "Route"}
        command = CreateArticleCommand(
            data=ArticleInput(fields=fields), prices=ArticlePrices(base_price=Money(price))
        )
        article, _ = catalog.create.execute(owner, command)
        items.append(
            StockedItem(
                article_id=article.id,
                opening=Decimal(opening),
                unit_cost=cost,
                sales=options((1, price, None)),
            )
        )
    return items


_PEOPLE = staff(
    1,
    ("Gérant", "Vendeur", "Vendeur", "Comptable"),
    ("Alhadji Moussa Bouba", "Paul Ndjock", "Issa Hamadou", "Aïcha Mbarga"),
)

MOTOS_PLAN = ShopPlan(
    profile=ProfileCode.MOTOS,
    name="Démo Motos",
    city="Garoua",
    phone="690001100",
    owner=_PEOPLE[0],
    sellers=(_PEOPLE[1], _PEOPLE[2]),
    accountant=_PEOPLE[3],
    suppliers=("Haojue Cameroun (Douala)", "Bajaj Afrique Centrale", "Import Nigeria Moto"),
    expenses=(
        Expense("Carburant", 25_000, "Essai des motos livrées", 5),
        Expense("Loyer", 150_000, "Loyer du magasin", 2),
    ),
    catalog=build_motos,
    customer=("Ibrahim Saïdou (moto-taxi)", "677451230"),
)
