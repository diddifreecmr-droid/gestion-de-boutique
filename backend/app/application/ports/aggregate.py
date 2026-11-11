"""Forme minimale d'un agrégat persistable et déclaration des contraintes d'unicité.

Un agrégat expose son identifiant, sa boutique, sa `version` (verrou optimiste, specs § 5.1) et
son `EventCollector`. Convention de version :

- `0` : agrégat neuf, jamais enregistré ; `Repository.add` le passe à `1` ;
- chaque `Repository.update` réussi l'incrémente de 1.

Les adaptateurs copient l'état de l'agrégat : il doit donc être copiable (`copy.deepcopy`).
"""

from collections.abc import Callable, Hashable
from dataclasses import dataclass
from typing import Protocol

from app.domain.shared.events import EventCollector
from app.domain.shared.ids import EntityId, ShopId


class Aggregate(Protocol):
    """Contrat structurel attendu par les dépôts et l'unité de travail."""

    version: int

    @property
    def id(self) -> EntityId: ...

    @property
    def shop_id(self) -> ShopId: ...

    @property
    def events(self) -> EventCollector: ...


class AggregateTracker(Protocol):
    """Reçoit les agrégats lus (`saved=False`) ou écrits (`saved=True`) par un dépôt."""

    def track(self, aggregate: Aggregate, *, saved: bool) -> None: ...


@dataclass(frozen=True, slots=True)
class UniqueKey[AggT]:
    """Contrainte d'unicité métier, **à l'intérieur d'une boutique** (`Duplicate` si violée).

    `extract` renvoie la valeur contrainte (un tuple pour plusieurs colonnes) ou `None` pour
    « non contraint », comme `NULL` dans un index unique SQL. `name` sert de nom de contrainte
    (repris dans `Duplicate.details["constraint"]`).
    """

    name: str
    extract: Callable[[AggT], Hashable | None]
