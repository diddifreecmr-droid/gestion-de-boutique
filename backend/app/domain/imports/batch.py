"""Agrégat `ImportBatch` : un fichier importé, numéroté `IMP-000001` (RG-T05, UC-IMP-02/03).

- Numéro attribué sans trou par le port de numérotation, une séquence par boutique ; un lot
  annulé garde son numéro (NUM-01).
- `preview_id` : l'aperçu confirmé ; unique par boutique, il rend la confirmation idempotente
  (IMP-09 : le même aperçu confirmé deux fois renvoie le même lot, T33).
- `items` : **chaque** élément créé (article, mouvement de stock, client, créance,
  fournisseur) avec la ligne du fichier qui l'a créé : l'annulation (QC-6, T35) les retrouve
  pour les archiver ou désactiver — rien n'est effacé (RG-T02) — et libérer leurs noms,
  références et téléphones.
- Cycle de vie : `Importé → Annulé` ; annulation possible jusqu'au **7ᵉ jour calendaire
  inclus** après la date de l'import (journée de Douala) ; au-delà `IMPORT_CANCEL_TOO_LATE`.
  Le refus « une opération touche le lot » (`IMPORT_CANCEL_BLOCKED`) relève de l'application.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from uuid import UUID

from app.domain.audit.values import EntityRef, Performer
from app.domain.imports.errors import ImportCancelTooLate
from app.domain.imports.events import ImportCancelled, ImportRecorded
from app.domain.imports.ids import ImportBatchId, ImportPreviewId
from app.domain.imports.values import CANCEL_WINDOW_DAYS, ImportedEntity, ImportKind, ImportStatus
from app.domain.shared.business_day import business_date, require_aware
from app.domain.shared.doc_number import DocNumber, DocType
from app.domain.shared.errors import InvalidStateTransition
from app.domain.shared.events import EventCollector
from app.domain.shared.ids import ShopId, UserId


@dataclass(frozen=True, slots=True, order=True)
class ImportedItem:
    """Élément créé par le lot, et la ligne du fichier qui l'a créé."""

    line: int
    entity: ImportedEntity
    entity_id: UUID

    def __post_init__(self) -> None:
        object.__setattr__(self, "entity", ImportedEntity(self.entity))
        if not isinstance(self.entity_id, UUID) or isinstance(self.line, bool) or self.line < 2:
            msg = "ImportedItem : identifiant UUID et ligne de données (≥ 2) attendus"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True, kw_only=True)
class ImportCounts:
    rows_read: int
    rows_imported: int
    rows_ignored: int

    def __post_init__(self) -> None:
        values = (self.rows_read, self.rows_imported, self.rows_ignored)
        if any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in values):
            msg = "Compteurs d'un lot : entiers positifs attendus"
            raise ValueError(msg)
        if self.rows_imported + self.rows_ignored != self.rows_read:
            msg = "Lignes importées + ignorées ≠ lignes lues"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class Cancellation:
    at: datetime
    by: UserId


@dataclass(eq=False, kw_only=True)
class ImportBatch:
    id: ImportBatchId
    shop_id: ShopId
    number: DocNumber
    kind: ImportKind
    preview_id: ImportPreviewId
    source_file_key: str
    counts: ImportCounts
    items: tuple[ImportedItem, ...]
    imported_by: UserId
    imported_at: datetime
    status: ImportStatus = ImportStatus.IMPORTED
    cancellation: Cancellation | None = None
    version: int = 0
    events: EventCollector = field(default_factory=EventCollector, repr=False)

    def __post_init__(self) -> None:
        self.imported_at = require_aware(self.imported_at)
        self.kind = ImportKind(self.kind)
        self.status = ImportStatus(self.status)
        if self.number.doc_type is not DocType.IMPORT:
            msg = f"Numéro de lot IMP attendu, reçu {self.number}"
            raise ValueError(msg)
        if not self.source_file_key.strip():
            msg = "Lot sans fichier source"
            raise ValueError(msg)
        if len({(i.entity, i.entity_id) for i in self.items}) != len(self.items):
            msg = "Élément créé cité deux fois dans le lot"
            raise ValueError(msg)
        if (self.status is ImportStatus.CANCELLED) != (self.cancellation is not None):
            msg = "Un lot annulé, et lui seul, porte son annulation"
            raise ValueError(msg)

    @property
    def entity(self) -> EntityRef:
        return EntityRef("import_batch", self.id.value, str(self.number))

    @property
    def imported_on(self) -> date:
        return business_date(self.imported_at)

    @property
    def last_cancel_day(self) -> date:
        """Dernier jour d'annulation (inclus) : date de l'import + 7 jours calendaires."""
        return self.imported_on + timedelta(days=CANCEL_WINDOW_DAYS)

    @classmethod
    def record(
        cls,
        shop_id: ShopId,
        number: DocNumber,
        kind: ImportKind,
        *,
        preview_id: ImportPreviewId,
        source_file_key: str,
        counts: ImportCounts,
        items: tuple[ImportedItem, ...],
        performer: Performer,
        now: datetime,
        batch_id: ImportBatchId | None = None,
    ) -> "ImportBatch":
        """`batch_id` : choisi avant l'écriture des éléments, qui citent leur lot (T33)."""
        batch = cls(
            id=batch_id or ImportBatchId.new(),
            shop_id=shop_id,
            number=number,
            kind=kind,
            preview_id=preview_id,
            source_file_key=source_file_key,
            counts=counts,
            items=tuple(sorted(items)),
            imported_by=performer.user_id,
            imported_at=now,
        )
        summary = (
            f"Import {batch.kind.label} {number} : {counts.rows_imported} ligne(s) importée(s),"
            f" {counts.rows_ignored} ignorée(s)"
        )
        batch.events.record(
            ImportRecorded(
                shop_id=shop_id,
                occurred_at=now,
                performer=performer,
                entity=batch.entity,
                summary=summary,
            )
        )
        return batch

    def cancel(self, *, performer: Performer, now: datetime) -> None:
        """Annule le lot (QC-6) ; l'appelant archive ou désactive les éléments (T35)."""
        if self.status is not ImportStatus.IMPORTED:
            msg = "Ce lot est déjà annulé"
            raise InvalidStateTransition(msg, details={"status": self.status.value})
        if business_date(now) > self.last_cancel_day:
            raise ImportCancelTooLate(self.imported_on, self.last_cancel_day)
        self.status = ImportStatus.CANCELLED
        self.cancellation = Cancellation(require_aware(now), performer.user_id)
        self.events.record(
            ImportCancelled(
                shop_id=self.shop_id,
                occurred_at=now,
                performer=performer,
                entity=self.entity,
                summary=f"Import {self.number} annulé ({len(self.items)} élément(s))",
            )
        )
