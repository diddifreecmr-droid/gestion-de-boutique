"""Port `ShopDataCensus` : combien de données métier la boutique a-t-elle ? (QC-1, T27)

Sert au changement de type (`ChangeShopProfile`) : il n'est permis que si tout vaut zéro.
Compte, dans la transaction de l'unité de travail, les articles (archivés compris), mouvements
de stock, ventes, achats, dépenses et créances de la boutique, quel que soit leur état (une
vente annulée compte). Adaptateurs : `memory/census.py`, `sqlalchemy/census.py` (contrat :
`tests/contracts/test_census_contract.py`).
"""

from abc import abstractmethod
from collections.abc import Mapping

from app.application.ports.shop_bound import ShopBoundPort
from app.domain.shops.profile_change import BlockingKind


class ShopDataCensus(ShopBoundPort):
    @abstractmethod
    def counts(self) -> Mapping[BlockingKind, int]:
        """Nombre d'éléments par nature de `DATA_KINDS`, zéros compris (chaque nature présente)."""
