"""Gabarit générique de dépôt **lié à une boutique** (TR-03, specs § 8.3, D4).

La boutique est un paramètre de **construction** : aucune méthode n'accepte de `shop_id`
libre. Ce gabarit fixe la sémantique commune à tous les adaptateurs ; un adaptateur ne fournit
que trois primitives de stockage (`_load`, `_insert`, `_save`).

Sémantique (vérifiée par `tests/contracts`) :

- `get(id)` lève `NotFound` si l'élément est absent **ou appartient à une autre boutique** —
  même erreur, même message : l'existence ne fuit pas ;
- `add` exige un agrégat neuf (version 0) de la boutique du dépôt et le passe en version 1 ;
  identifiant déjà pris ou contrainte d'unicité violée → `Duplicate` ;
- `update` applique le verrou optimiste : version attendue ≠ version stockée →
  `VersionConflict` ; élément absent de la boutique → `NotFound`.

Un agrégat d'une autre boutique passé à `add`/`update` est un bogue : `IsolationViolation`.

Accès depuis une unité de travail : `WidgetRepository.within(uow)` (typé, sans transtypage).
"""

from abc import abstractmethod
from collections.abc import Sequence

from app.application.ports.aggregate import Aggregate, UniqueKey
from app.application.ports.errors import IsolationViolation
from app.application.ports.shop_bound import PortProvider, ShopBoundPort
from app.domain.shared.errors import NotFound
from app.domain.shared.ids import EntityId

NOT_FOUND_MESSAGE = "Élément introuvable"


def not_found(entity_id: EntityId) -> NotFound:
    """Erreur unique pour « absent » comme pour « autre boutique » (aucune fuite)."""
    return NotFound(NOT_FOUND_MESSAGE, details={"id": str(entity_id)})


RepositoryProvider = PortProvider
"""Ancien nom du fournisseur de ports (une unité de travail), conservé pour compatibilité."""


class Repository[IdT: EntityId, AggT: Aggregate](ShopBoundPort):
    """Base de tout port de dépôt : `class SaleRepository(Repository[SaleId, Sale])`.

    Construction, `within(uow)` et `shop_id` viennent de `ShopBoundPort`.
    """

    def unique_keys(self) -> Sequence[UniqueKey[AggT]]:
        """Contraintes d'unicité métier du port, par boutique. Aucune par défaut."""
        return ()

    # ------------------------------------------------------------------ opérations
    def get(self, entity_id: IdT) -> AggT:
        aggregate = self._load(entity_id)
        if aggregate is None:
            raise not_found(entity_id)
        if aggregate.shop_id != self._shop_id:
            msg = f"{type(self).__name__}._load a renvoyé un agrégat d'une autre boutique"
            raise IsolationViolation(msg)
        self._tracker.track(aggregate, saved=False)
        return aggregate

    def add(self, aggregate: AggT) -> None:
        self._require_own_shop(aggregate)
        if aggregate.version != 0:
            msg = f"add attend un agrégat neuf (version 0), reçu la version {aggregate.version}"
            raise ValueError(msg)
        aggregate.version = 1
        try:
            self._insert(aggregate)
        except BaseException:
            aggregate.version = 0  # l'agrégat de l'appelant reste cohérent avec la base
            raise
        self._tracker.track(aggregate, saved=True)

    def update(self, aggregate: AggT) -> None:
        self._require_own_shop(aggregate)
        expected = aggregate.version
        if expected < 1:
            msg = "update attend un agrégat déjà enregistré (version ≥ 1) : utiliser add"
            raise ValueError(msg)
        aggregate.version = expected + 1
        try:
            self._save(aggregate, expected_version=expected)
        except BaseException:
            aggregate.version = expected
            raise
        self._tracker.track(aggregate, saved=True)

    def _require_own_shop(self, aggregate: AggT) -> None:
        if aggregate.shop_id != self._shop_id:
            msg = f"Agrégat d'une autre boutique transmis à {type(self).__name__}"
            raise IsolationViolation(msg)

    # ------------------------------------------------------------------ primitives d'adaptateur
    @abstractmethod
    def _load(self, entity_id: IdT) -> AggT | None:
        """Copie de l'agrégat **de la boutique du dépôt** ou `None` (filtre `shop_id` requis)."""

    @abstractmethod
    def _insert(self, aggregate: AggT) -> None:
        """Enregistre un agrégat neuf (déjà en version 1) ; `Duplicate` si id ou clé pris."""

    @abstractmethod
    def _save(self, aggregate: AggT, *, expected_version: int) -> None:
        """Remplace l'état stocké en version `expected_version` par `aggregate` (déjà incrémenté).

        `NotFound` (via `not_found`) si absent de la boutique ; `VersionConflict` si la version
        stockée diffère ; `Duplicate` si une contrainte d'unicité est violée.
        """
