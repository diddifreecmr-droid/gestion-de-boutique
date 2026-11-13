import { useState } from "react";
import { Download } from "lucide-react";
import type { ImportBatchDetail } from "../../core/gateways/importsContract";
import { useImports } from "../../core/gateways/httpImports";
import { formatDate, formatTime } from "../../shared/format";
import { Button } from "../../shared/ui";
import { asError } from "../expenses/useLoad";
import { BatchBadge } from "./BatchList";
import { dayMonth, stillCancellable } from "./batchText";
import { CancelImport, type CancelOutcome } from "./CancelImport";
import { CountLine, CountList } from "./CountLine";
import { importFailure } from "./importErrors";
import { createdText, linesText, modelOf } from "./importModels";
import type { SaveFile } from "./saveFile";

export const ERRORS_LABEL = "Télécharger les erreurs";

export interface BatchDetailProps {
  shopId: string;
  batch: ImportBatchDetail;
  today: string;
  /** Propriétaire : seul à pouvoir annuler un lot. */
  canCancel: boolean;
  save: SaveFile;
  /** Issue d'une annulation (affichée et relue par l'appelant). */
  onOutcome: (outcome: CancelOutcome | null) => void;
}

/**
 * Détail d'un lot (T45) : auteur, éléments créés, problèmes relevés, « Télécharger les
 * erreurs » (`errors.xlsx`) et, pour le propriétaire, « Annuler l'import » dans le délai.
 */
export function BatchDetail({
  shopId,
  batch,
  today,
  canCancel,
  save,
  onOutcome,
}: BatchDetailProps) {
  const gateway = useImports();
  const [downloading, setDownloading] = useState(false);
  const [downloadFailure, setDownloadFailure] = useState<string | null>(null);
  const [fatal, setFatal] = useState<unknown>(null);
  if (fatal !== null) throw asError(fatal);

  const download = async () => {
    setDownloading(true);
    setDownloadFailure(null);
    try {
      save(await gateway.errors(shopId, batch.id));
    } catch (error) {
      try {
        setDownloadFailure(importFailure(error).text);
      } catch (unexpected) {
        setFatal(unexpected);
      }
    } finally {
      setDownloading(false);
    }
  };

  return (
    <>
      <div className="flex flex-wrap items-center gap-2">
        <p className="m-0 text-body text-text-muted">
          {modelOf(batch.kind).label} · le {formatDate(batch.imported_at)} à{" "}
          {formatTime(batch.imported_at)} · par {batch.imported_by.name}
        </p>
        <BatchBadge batch={batch} />
      </div>
      <CountList label="Bilan du lot">
        <CountLine tone="success">{`${linesText(batch.rows_imported)} importée${batch.rows_imported > 1 ? "s" : ""}`}</CountLine>
        {batch.rows_ignored > 0 && (
          <CountLine tone="danger">{`${linesText(batch.rows_ignored)} ignorée${batch.rows_ignored > 1 ? "s" : ""}`}</CountLine>
        )}
        {batch.created.map((created) => (
          <CountLine key={created.entity} tone="muted">
            {createdText(created.entity, created.count)}
          </CountLine>
        ))}
        {batch.problems_total > 0 && (
          <CountLine tone="danger">
            {`${batch.problems_total.toLocaleString("fr-FR")} problème${batch.problems_total > 1 ? "s" : ""} relevé${batch.problems_total > 1 ? "s" : ""}`}
          </CountLine>
        )}
      </CountList>
      {batch.problems_total > 0 && (
        <Button
          variant="secondary"
          icon={Download}
          loading={downloading}
          onClick={() => {
            void download();
          }}
        >
          {ERRORS_LABEL}
        </Button>
      )}
      {downloadFailure !== null && (
        <p role="alert" className="m-0 text-body text-danger-text">
          {downloadFailure}
        </p>
      )}
      {batch.status === "cancelled" && batch.cancelled_at !== null && (
        <p className="m-0 text-body text-text-muted">
          Annulé le {formatDate(batch.cancelled_at)} : les éléments sont archivés.
        </p>
      )}
      {canCancel && batch.status === "imported" && !stillCancellable(batch, today) && (
        <p className="m-0 text-body text-text-muted">
          Délai dépassé : annulation possible jusqu'au {dayMonth(batch.cancellable_until)}.
        </p>
      )}
      {canCancel && stillCancellable(batch, today) && (
        <CancelImport shopId={shopId} batch={batch} onOutcome={onOutcome} />
      )}
    </>
  );
}
