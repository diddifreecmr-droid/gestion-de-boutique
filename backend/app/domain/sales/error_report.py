"""Agrégat `ErrorReport` : signalement d'erreur sur une vente (UC-VEN-06, CDC § 20.4).

- Le vendeur décrit le problème sur **l'une de ses ventes** (« mauvais prix, c'était
  750 000 ») ; le propriétaire reçoit l'alerte « Erreur signalée » (`ErrorReported`).
- Le propriétaire répond (texte visible par le vendeur) et le passe « Traité » ; il corrige ou
  annule la vente par ailleurs (UC-VEN-07, UC-VEN-08). Le vendeur voit la suite donnée (RPT-02).
- Statuts : Ouvert → Traité. Une réponse sur un signalement traité la remplace (nouvelle
  précision), avant/après au journal.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from app.domain.audit.values import EntityRef, FieldChange, Performer
from app.domain.sales.events import ErrorReportAnswered, ErrorReported
from app.domain.sales.ids import ErrorReportId, SaleId
from app.domain.shared.business_day import require_aware
from app.domain.shared.events import EventCollector
from app.domain.shared.ids import ShopId, UserId
from app.domain.shops.values import clean_text

TEXT_MAX_LENGTH = 500


class ReportStatus(StrEnum):
    OPEN = "open"  # Ouvert
    HANDLED = "handled"  # Traité


@dataclass(eq=False, kw_only=True)
class ErrorReport:
    id: ErrorReportId
    shop_id: ShopId
    sale_id: SaleId
    sale_number: str
    reported_by: UserId
    description: str
    reported_at: datetime
    status: ReportStatus = ReportStatus.OPEN
    owner_reply: str | None = None
    replied_at: datetime | None = None
    replied_by: UserId | None = None
    version: int = 0
    events: EventCollector = field(default_factory=EventCollector, repr=False)

    def __post_init__(self) -> None:
        self.reported_at = require_aware(self.reported_at)
        self.status = ReportStatus(self.status)
        if self.replied_at is not None:
            self.replied_at = require_aware(self.replied_at)

    @property
    def entity(self) -> EntityRef:
        return EntityRef("sale", self.sale_id.value, self.sale_number)

    @classmethod
    def report(
        cls,
        shop_id: ShopId,
        sale_id: SaleId,
        sale_number: str,
        description: str,
        *,
        performer: Performer,
        now: datetime,
        report_id: ErrorReportId | None = None,
    ) -> "ErrorReport":
        text = clean_text(description, "description", max_length=TEXT_MAX_LENGTH)
        report = cls(
            id=report_id or ErrorReportId.new(),
            shop_id=shop_id,
            sale_id=sale_id,
            sale_number=sale_number,
            reported_by=performer.user_id,
            description=text,
            reported_at=now,
        )
        report.events.record(
            ErrorReported(
                shop_id=shop_id,
                occurred_at=now,
                performer=performer,
                entity=report.entity,
                summary=f"Erreur signalée sur la vente {sale_number} : {text}"[:500],
                sale_number=sale_number,
            )
        )
        return report

    def answer(self, reply: str, *, handled: bool, performer: Performer, now: datetime) -> None:
        """Réponse du propriétaire ; `handled` passe le signalement « Traité »."""
        text = clean_text(reply, "reply", max_length=TEXT_MAX_LENGTH)
        status = ReportStatus.HANDLED if handled else self.status
        changes = tuple(
            FieldChange(name, before, after)
            for name, before, after in (
                ("owner_reply", self.owner_reply, text),
                ("status", self.status.value, status.value),
            )
            if before != after
        )
        self.owner_reply, self.status = text, status
        self.replied_at, self.replied_by = now, performer.user_id
        self.events.record(
            ErrorReportAnswered(
                shop_id=self.shop_id,
                occurred_at=now,
                performer=performer,
                entity=self.entity,
                summary=f"Réponse au signalement sur la vente {self.sale_number}",
                changes=changes,
            )
        )
