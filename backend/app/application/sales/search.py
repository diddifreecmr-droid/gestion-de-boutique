"""Critères de la liste des ventes (UC-VEN-05) et lecture d'un terme de recherche (RG-M02).

`reference_terms("v-000124")` → numéro `V-000124` (comparé tel quel au numéro définitif ou
provisoire `V-HL-3F2A-0007`, sans casse ni espace) et clé de châssis `V000124` ; la requête
cherche l'un **ou** l'autre. Un terme
sans lettre ni chiffre → 400 (aucune recherche silencieusement vide).
"""

from dataclasses import dataclass
from datetime import date

from app.domain.catalog.ids import ArticleId
from app.domain.sales.chassis import chassis_key
from app.domain.sales.sale import Sale
from app.domain.sales.values import SaleKind
from app.domain.shared.doc_number import DocType
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.ids import UserId
from app.domain.shops.ids import PaymentModeId

TEXT_MAX_LENGTH = 64


@dataclass(frozen=True, slots=True, kw_only=True)
class SaleCriteria:
    first_day: date | None = None
    last_day: date | None = None
    seller_id: UserId | None = None
    article_id: ArticleId | None = None
    payment_mode_id: PaymentModeId | None = None
    kind: SaleKind | None = None
    text: str | None = None

    def __post_init__(self) -> None:
        text = None if self.text is None else self.text.strip() or None
        if text is not None and len(text) > TEXT_MAX_LENGTH:
            msg = f"Recherche de {TEXT_MAX_LENGTH} caractères au plus"
            raise ValidationFailed(msg, details={"field": "q"})
        object.__setattr__(self, "text", text)

    def matches(self, sale: Sale) -> bool:
        content = sale.content
        return (
            (self.kind is None or sale.kind is self.kind)
            and (
                self.article_id is None
                or any(line.article_id == self.article_id for line in content.lines)
            )
            and (
                self.payment_mode_id is None
                or any(p.mode_id == self.payment_mode_id for p in content.payments)
            )
        )


def reference_terms(text: str) -> tuple[str | None, str | None]:
    """(numéro normalisé ou `None`, clé de châssis) d'un terme de recherche."""
    candidate = "".join(text.split()).upper()
    number = candidate if candidate.startswith(f"{DocType.SALE.value}-") else None
    return number, chassis_key(text)
