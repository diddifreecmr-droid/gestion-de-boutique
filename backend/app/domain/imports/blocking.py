"""Opérations qui empêchent d'annuler un lot (décision client QC-6, UC-IMP-03).

Un lot ne s'annule pas si une opération **touche** un de ses éléments : une vente (ou son
retour), un achat, un ajustement, un inventaire, un versement sur une créance reprise, ou un
**autre lot** encore importé (stock de départ posé sur un article du lot, créance reprise sur un
client du lot). `details.blocking` de `IMPORT_CANCEL_BLOCKED` les cite par type et numéro :
`[{type: "sale", number: "V-000003"}]`.
"""

from dataclasses import dataclass
from enum import StrEnum

NUMBER_MAX_LENGTH = 120


class BlockingType(StrEnum):
    SALE = "sale"
    SALE_RETURN = "return"
    PURCHASE = "purchase"
    ADJUSTMENT = "adjustment"
    INVENTORY = "inventory"
    PAYMENT = "payment"  # Versement sur créance (R-…)
    RECEIVABLE = "receivable"  # Créance ancienne saisie à la main sur un client du lot
    IMPORT = "import"  # Autre lot encore importé


@dataclass(frozen=True, slots=True, order=True)
class BlockingOperation:
    type: BlockingType
    number: str
    """Numéro lisible (`V-000003`, `R-000001`, `IMP-000002`) ou, à défaut, libellé court."""

    def __post_init__(self) -> None:
        object.__setattr__(self, "type", BlockingType(self.type))
        number = self.number.strip() if isinstance(self.number, str) else ""
        if not number:
            msg = "Opération bloquante sans numéro ni libellé"
            raise ValueError(msg)
        object.__setattr__(self, "number", number[:NUMBER_MAX_LENGTH])

    def as_detail(self) -> dict[str, str]:
        return {"type": self.type.value, "number": self.number}
