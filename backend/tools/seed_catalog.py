"""Catalogue de démonstration (**dev uniquement**) : six modèles de motos avec leur prix de base.

Créés par le vrai cas d'utilisation `CreateArticle`, comme le propriétaire (prix de base fixés
et inscrits à l'historique). Appelé par `tools/seed_dev.py` à l'ouverture de la boutique.
"""

from app.application.catalog.use_cases.context import ArticleInput
from app.application.catalog.use_cases.create_article import CreateArticleCommand
from app.application.security.actor import Actor
from app.bootstrap.catalog import build_catalog
from app.bootstrap.identity import IdentityModule
from app.domain.catalog.prices import ArticlePrices
from app.domain.shared.money import Money

ROAD = "Moto de route"
MOTOS = (
    ("Haojue", "HJ125-8", 125, 780_000),
    ("Haojue", "DK150", 150, 950_000),
    ("Bajaj", "Boxer BM150", 150, 850_000),
    ("TVS", "HLX 125", 125, 690_000),
    ("Sanili", "SL125-7", 125, 620_000),
    ("Nanfang", "NF125-2", 125, 600_000),
)
"""(marque, modèle, cylindrée en cm³, prix de base en FCFA)."""


def seed_motos(identity: IdentityModule, owner: Actor) -> int:
    """Crée les six modèles ; renvoie le nombre d'articles créés."""
    create = build_catalog(identity).http.create
    for brand, model, engine_cc, price in MOTOS:
        fields = {"brand": brand, "model": model, "engine_cc": engine_cc, "category": ROAD}
        command = CreateArticleCommand(
            data=ArticleInput(fields=fields), prices=ArticlePrices(base_price=Money(price))
        )
        create.execute(owner, command)
    return len(MOTOS)
