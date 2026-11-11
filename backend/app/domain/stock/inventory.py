"""Agrégat `Inventory` : comptage physique d'un lieu (UC-STK-07, recette INV-01 à INV-06).

Cycle de vie : En cours → Validé, ou En cours → Abandonné (aucune autre transition).

1. Lancement : numéro `INV-000001`, une ligne par article actif du catalogue ; un seul
   inventaire en cours par lieu (`open_location_key`, contrainte `inventory_open_location`).
2. Comptage (`record_counts`) : par morceaux, reprise possible ; une quantité `None` efface un
   comptage. La quantité théorique n'existe pas encore (masquée, INV-01).
3. Validation (`validate`) : toutes les lignes comptées ; théorique lu **à la validation**
   (Q-17) ; motif exigé pour chaque écart non nul, sauf motif global (`ReasonRequired`, 400).
   L'appelant crée ensuite un ajustement par écart et alerte le propriétaire.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from app.domain.audit.values import EntityRef, Performer
from app.domain.catalog.ids import ArticleId
from app.domain.shared.business_day import require_aware
from app.domain.shared.doc_number import DocNumber
from app.domain.shared.errors import InvalidStateTransition, ValidationFailed
from app.domain.shared.events import EventCollector
from app.domain.shared.ids import ShopId
from app.domain.shared.money import Money
from app.domain.shared.quantity import Quantity, StockUnit
from app.domain.shops.ids import LocationId
from app.domain.shops.values import clean_optional
from app.domain.stock.errors import ReasonRequired
from app.domain.stock.events import (
    InventoryAbandoned,
    InventoryCounted,
    InventoryStarted,
    InventoryValidated,
)
from app.domain.stock.ids import InventoryId
from app.domain.stock.inventory_line import InventoryLine, LineCheck
from app.domain.stock.valuation import total_or_none

REASON_MAX_LENGTH = 500


class InventoryStatus(StrEnum):
    IN_PROGRESS = "in_progress"  # En cours
    VALIDATED = "validated"  # Validé
    ABANDONED = "abandoned"  # Abandonné


@dataclass(eq=False, kw_only=True)
class Inventory:
    id: InventoryId
    shop_id: ShopId
    number: DocNumber
    location_id: LocationId
    started_at: datetime
    lines: dict[ArticleId, InventoryLine]
    status: InventoryStatus = InventoryStatus.IN_PROGRESS
    closed_at: datetime | None = None
    global_reason: str | None = None
    version: int = 0
    events: EventCollector = field(default_factory=EventCollector, repr=False)

    def __post_init__(self) -> None:
        self.status = InventoryStatus(self.status)
        self.started_at = require_aware(self.started_at)

    @property
    def entity(self) -> EntityRef:
        return EntityRef("inventory", self.id.value, str(self.number))

    @property
    def open_location_key(self) -> LocationId | None:
        """Clé « un seul en cours par lieu » : le lieu tant que l'inventaire est ouvert."""
        return self.location_id if self.status is InventoryStatus.IN_PROGRESS else None

    @property
    def gaps(self) -> list[InventoryLine]:
        return [line for line in self.lines.values() if line.has_gap]

    @property
    def gap_value(self) -> Money | None:
        return total_or_none(line.gap_value for line in self.gaps)

    @classmethod
    def start(
        cls,
        *,
        shop_id: ShopId,
        number: DocNumber,
        location_id: LocationId,
        articles: Sequence[tuple[ArticleId, StockUnit]],
        performer: Performer,
        now: datetime,
        inventory_id: InventoryId | None = None,
    ) -> "Inventory":
        lines = {aid: InventoryLine(article_id=aid, unit=unit) for aid, unit in articles}
        inventory = cls(
            id=inventory_id or InventoryId.new(),
            shop_id=shop_id,
            number=number,
            location_id=location_id,
            started_at=now,
            lines=lines,
        )
        inventory._record(InventoryStarted, performer, now, f"Inventaire lancé : {number}")
        return inventory

    def record_counts(
        self, counts: Mapping[ArticleId, Quantity | None], *, performer: Performer, now: datetime
    ) -> None:
        self._require_open("compter")
        unknown = sorted(str(aid) for aid in counts if aid not in self.lines)
        if unknown:
            msg = "Article absent de cet inventaire"
            raise ValidationFailed(msg, details={"field": "counts", "articles": unknown})
        for article_id, counted in counts.items():
            self.lines[article_id] = self.lines[article_id].count(counted)
        summary = f"Comptage enregistré ({len(counts)} article(s)) : {self.number}"
        self._record(InventoryCounted, performer, now, summary)

    def validate(
        self,
        checks: Mapping[ArticleId, LineCheck],
        *,
        reasons: Mapping[ArticleId, str],
        global_reason: str | None,
        performer: Performer,
        now: datetime,
    ) -> list[InventoryLine]:
        """Fige les écarts ; renvoie les lignes en écart (chacune deviendra un ajustement)."""
        self._require_open("valider")
        missing = sorted(str(aid) for aid, line in self.lines.items() if line.counted is None)
        if missing:
            msg = "Toutes les lignes doivent être comptées avant la validation"
            raise ValidationFailed(msg, details={"field": "counts", "articles": missing})
        motive = clean_optional(global_reason, "global_reason", max_length=REASON_MAX_LENGTH)
        settled = {}
        for article_id, line in self.lines.items():
            own = clean_optional(reasons.get(article_id), "reason", max_length=REASON_MAX_LENGTH)
            settled[article_id] = line.settle(checks[article_id], own or motive)
        lacking = sorted(str(a) for a, line in settled.items() if line.has_gap and not line.reason)
        if lacking:
            raise ReasonRequired(lacking)
        self.lines, self.global_reason = settled, motive
        self.status, self.closed_at = InventoryStatus.VALIDATED, require_aware(now)
        self.events.record(
            InventoryValidated(
                shop_id=self.shop_id,
                occurred_at=now,
                performer=performer,
                entity=self.entity,
                summary=f"Inventaire validé : {self.number} ({len(self.gaps)} écart(s))",
                reason=motive,
                gap_count=len(self.gaps),
                gap_value=self.gap_value,
            )
        )
        return self.gaps

    def abandon(self, *, performer: Performer, now: datetime) -> None:
        self._require_open("abandonner")
        self.status, self.closed_at = InventoryStatus.ABANDONED, require_aware(now)
        self._record(InventoryAbandoned, performer, now, f"Inventaire abandonné : {self.number}")

    def _require_open(self, action: str) -> None:
        if self.status is not InventoryStatus.IN_PROGRESS:
            msg = f"Impossible de {action} un inventaire qui n'est plus en cours"
            raise InvalidStateTransition(msg, details={"status": self.status.value})

    def _record(
        self,
        event: type[InventoryStarted | InventoryCounted | InventoryAbandoned],
        performer: Performer,
        now: datetime,
        summary: str,
    ) -> None:
        self.events.record(
            event(
                shop_id=self.shop_id,
                occurred_at=now,
                performer=performer,
                entity=self.entity,
                summary=summary,
            )
        )
