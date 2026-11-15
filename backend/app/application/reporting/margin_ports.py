"""Port de requête `MarginQueries` (Coûts et marges, specs § 15.1, 2026-11-15) : sommes brutes des
lignes vendues par journée et par article, aux **coûts figés au moment de la vente** (dernier
coût, RG-T15).

Sémantique commune aux adaptateurs mémoire et SQL (`tests/contracts/test_margins_contract.py`) :

- ventes datées de la période (`sold_on`), **non annulées** (une vente annulée ne rapporte rien) ;
  les retours ne sont pas déduits (ils restent dans le tableau de bord, journée du retour) ;
- `quantity` : quantité **en unité de stock** (mètres en Textile) ;
- `cost` et `costed_revenue` : lignes dont le coût figé est connu ; `without_cost` : les autres ;
- nom, tissu, unité et longueur du rouleau : ceux de l'article **maintenant** ; article introuvable
  → nom figé de la ligne, unité de la ligne, ni tissu ni rouleau.

Aucun indicateur n'est calculé ici (`margins.py`).
"""

from abc import abstractmethod
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.application.ports.shop_bound import ShopBoundPort
from app.domain.catalog.ids import ArticleId
from app.domain.shared.quantity import StockUnit


@dataclass(frozen=True, slots=True, kw_only=True)
class ArticleDaySales:
    day: date
    article_id: ArticleId
    name: str
    fabric: str | None
    stock_unit: StockUnit
    roll_length_m: Decimal | None
    quantity: Decimal
    costed_quantity: Decimal
    """Quantité des seules lignes à coût connu (base des chiffres au mètre et au rouleau)."""
    revenue: int
    costed_revenue: int
    """Chiffre d'affaires des seules lignes à coût connu (base du taux de marge)."""
    cost: int
    without_cost: int = 0


class MarginQueries(ShopBoundPort):
    """Agrégats en lecture seule ; liste triée par journée puis par identifiant d'article."""

    @abstractmethod
    def sold_by_article(self, first_day: date, last_day: date) -> list[ArticleDaySales]:
        """Lignes des ventes non annulées de la période, par journée et article."""
