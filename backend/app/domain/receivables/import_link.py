"""Créance ancienne reprise par un import, puis annulée avec son lot (décision client QC-6).

`cancel_with_import` : la créance passe **Annulée** (hors total à recevoir, rien d'effacé). Elle
réutilise l'annulation de la créance (`sale_cancellation` : jour de Douala et instant ; une
créance ancienne n'a pas de vente, aucune confusion possible). Refus si elle porte un versement
valide : l'annulation du lot doit déjà l'avoir refusée (`IMPORT_CANCEL_BLOCKED`), c'est donc une
erreur d'appelant.
"""

from datetime import date, datetime

from app.domain.audit.values import Performer
from app.domain.receivables.events import LegacyReceivableCancelled
from app.domain.receivables.state import ReceivableState
from app.domain.receivables.values import ReceivableOrigin, SaleCancellation


class ImportLink(ReceivableState):
    def cancel_with_import(
        self, *, number: str, performer: Performer, on: date, at: datetime
    ) -> None:
        if self.origin is not ReceivableOrigin.LEGACY:
            msg = "Seule une créance ancienne s'annule avec son import"
            raise ValueError(msg)
        self.require_not_cancelled()
        if any(item.valid for item in self.installments):
            msg = "Une créance avec un versement ne s'annule pas avec son import"
            raise ValueError(msg)
        self.sale_cancellation = SaleCancellation(on, at)
        self.events.record(
            LegacyReceivableCancelled(
                shop_id=self.shop_id,
                occurred_at=at,
                performer=performer,
                entity=self.entity,
                summary=f"Créance ancienne annulée avec l'import {number}",
            )
        )
