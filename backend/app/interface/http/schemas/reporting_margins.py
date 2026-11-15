"""Réponse « Coûts et marges » du gérant (`GET /shops/{id}/dashboard/margins`, specs § 15.1).

Propriétaire seul. Montants en entiers FCFA ; quantités en chaînes décimales (unité de stock :
mètres en Textile) ; taux de marge en chaîne à 2 chiffres (`"28.57"`), `null` sans chiffre
d'affaires à coût connu ; `without_cost` : lignes sans coût figé, exclues du coût et de la marge
(RG-T15). `per_meter` et `per_roll` : Textile seulement, sinon `null`.
"""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.interface.http.schemas.reporting import PeriodOut


class _Out(BaseModel):
    model_config = ConfigDict(frozen=True)


class MarginFigures(_Out):
    revenue: int
    cost: int
    margin: int
    margin_rate: str | None
    without_cost: int


class PerUnitOut(_Out):
    price: int
    cost: int
    margin: int


class ArticleMarginOut(_Out):
    article_id: UUID
    name: str
    fabric: str | None
    stock_unit: str
    quantity: str
    figures: MarginFigures
    roll_length_m: str | None
    per_meter: PerUnitOut | None
    per_roll: PerUnitOut | None


class FabricMarginOut(_Out):
    fabric: str
    colors: int
    quantity: str
    figures: MarginFigures
    roll_length_m: str | None
    per_meter: PerUnitOut | None
    per_roll: PerUnitOut | None


class DayMarginOut(_Out):
    day: date
    revenue: int
    cost: int
    margin: int


class MarginsResponse(_Out):
    period: PeriodOut
    totals: MarginFigures
    articles: list[ArticleMarginOut]
    fabrics: list[FabricMarginOut]
    days: list[DayMarginOut]
