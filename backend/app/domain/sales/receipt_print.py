"""Agrégat `ReceiptPrint` : une impression (ou un partage) du reçu d'une vente (UC-VEN-04).

Chaque demande du reçu est inscrite (RG-T01 « impression ») avec son **rang** : 1 = original,
2 et plus = « Duplicata » (RCP-03, Q-25 tranchée : la mention apparaît dès la 2ᵉ demande, quel
que soit l'utilisateur). Le rang est unique par vente (contrainte `receipt_print_sequence`) :
deux demandes simultanées ne peuvent pas être toutes deux l'original (la seconde est rejouée).
Une impression ne touche jamais la vente (sa `version` ne bouge pas).
"""

from dataclasses import dataclass, field
from datetime import datetime

from app.domain.audit.values import EntityRef, Performer
from app.domain.sales.events import ReceiptPrinted
from app.domain.sales.ids import ReceiptPrintId, SaleId
from app.domain.shared.business_day import require_aware
from app.domain.shared.events import EventCollector
from app.domain.shared.ids import ShopId, UserId


@dataclass(eq=False, kw_only=True)
class ReceiptPrint:
    id: ReceiptPrintId
    shop_id: ShopId
    sale_id: SaleId
    sequence: int
    printed_at: datetime
    printed_by: UserId
    version: int = 0
    events: EventCollector = field(default_factory=EventCollector, repr=False)

    def __post_init__(self) -> None:
        self.printed_at = require_aware(self.printed_at)
        if isinstance(self.sequence, bool) or not isinstance(self.sequence, int):
            msg = "ReceiptPrint.sequence doit être un int"
            raise TypeError(msg)
        if self.sequence < 1:
            msg = "Le rang d'une impression commence à 1"
            raise ValueError(msg)

    @property
    def is_duplicate(self) -> bool:
        return self.sequence > 1

    @property
    def sequence_key(self) -> tuple[SaleId, int]:
        return (self.sale_id, self.sequence)

    @classmethod
    def record(
        cls,
        shop_id: ShopId,
        sale_entity: EntityRef,
        sequence: int,
        *,
        performer: Performer,
        now: datetime,
    ) -> "ReceiptPrint":
        if sale_entity.id is None:
            msg = "Reçu d'une vente sans identifiant"
            raise ValueError(msg)
        printed = cls(
            id=ReceiptPrintId.new(),
            shop_id=shop_id,
            sale_id=SaleId(sale_entity.id),
            sequence=sequence,
            printed_at=now,
            printed_by=performer.user_id,
        )
        mention = " (duplicata)" if printed.is_duplicate else ""
        printed.events.record(
            ReceiptPrinted(
                shop_id=shop_id,
                occurred_at=now,
                performer=performer,
                entity=sale_entity,
                summary=f"Reçu de la vente {sale_entity.number} imprimé{mention}",
            )
        )
        return printed
