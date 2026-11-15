"""« Démo Prêt-à-porter » : dix articles génériques désignés par leur nom (SKU facultatif)."""

from decimal import Decimal

from app.application.catalog.use_cases.context import ArticleInput
from app.application.catalog.use_cases.create_article import CreateArticleCommand
from app.application.security.actor import Actor
from app.bootstrap.seed_demo.plan import Expense, ShopPlan, StockedItem, options, staff
from app.domain.catalog.prices import ArticlePrices
from app.domain.profiles.profile import ProfileCode
from app.domain.shared.money import Money
from app.interface.http.routes.catalog import CatalogComponents

ARTICLES = (
    ("Robette avec sac", None, "Femme", 15_000, 8_500, 12),
    ("Robette bleue", None, "Femme", 12_000, 6_500, 10),
    ("Pantalon et boubou", None, "Homme", 25_000, 14_000, 8),
    ("Chemise homme", "CH-001", "Homme", 8_000, 4_200, 20),
    ("Ensemble pagne", None, "Femme", 18_000, 10_000, 9),
    ("Jupe plissée", None, "Femme", 7_500, 3_800, 14),
    ("Tee-shirt enfant", "TE-010", "Enfant", 3_500, 1_600, 30),
    ("Kaba brodée", None, "Femme", 22_000, 12_500, 6),
    ("Jean homme", "JH-032", "Homme", 10_000, 5_500, 15),
    ("Sandales cuir", None, "Accessoires", 6_000, 3_000, 18),
)
"""(nom, référence facultative, catégorie, prix de vente, coût d'achat, stock initial)."""


def build_apparel(catalog: CatalogComponents, owner: Actor) -> list[StockedItem]:
    items = []
    for name, reference, category, price, cost, opening in ARTICLES:
        fields: dict[str, object] = {"name": name, "category": category}
        if reference is not None:
            fields["reference"] = reference
        command = CreateArticleCommand(
            data=ArticleInput(fields=fields), prices=ArticlePrices(base_price=Money(price))
        )
        article, _ = catalog.create.execute(owner, command)
        items.append(
            StockedItem(
                article_id=article.id,
                opening=Decimal(opening),
                unit_cost=cost,
                sales=options((1, price, None), (2, price, None)),
                restock=Decimal(5),
            )
        )
    return items


_PEOPLE = staff(
    2,
    ("Gérante", "Employée", "Employé", "Comptable"),
    ("Mireille Ngo Biyong", "Carine Fotso", "Junior Essomba", "Brice Tchamba"),
)

APPAREL_PLAN = ShopPlan(
    profile=ProfileCode.APPAREL,
    name="Démo Prêt-à-porter",
    city="Douala",
    phone="690001200",
    owner=_PEOPLE[0],
    sellers=(_PEOPLE[1], _PEOPLE[2]),
    accountant=_PEOPLE[3],
    suppliers=("Grossiste Marché Central", "Atelier Couture Akwa", "Import Dubaï Mode"),
    expenses=(
        Expense("Repas", 5_000, "Repas des employées (inventaire)", 5),
        Expense("Loyer", 80_000, "Loyer de la boutique", 2),
    ),
    catalog=build_apparel,
    customer=("Mme Ekambi Solange", "677451231"),
)
