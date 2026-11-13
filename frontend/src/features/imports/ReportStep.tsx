import { FileSpreadsheet } from "lucide-react";
import type { ImportBatch } from "../../core/gateways/importsContract";
import { formatDate, formatTime } from "../../shared/format";
import { Button } from "../../shared/ui";
import { CountLine, CountList } from "./CountLine";
import { createdText, linesText } from "./importModels";

export const AGAIN_LABEL = "Faire un autre import";

/**
 * Étape 4 : rapport du lot (IMP-10) — numéro `IMP-…`, lignes importées et ignorées, éléments
 * créés par type. Annoncé à l'arrivée (`role="status"`).
 */
export function ReportStep({ batch, onAgain }: { batch: ImportBatch; onAgain: () => void }) {
  return (
    <>
      <div role="status" className="flex flex-col gap-1">
        <p className="m-0 text-title-sm font-semibold text-success-text">
          Import {batch.number} enregistré
        </p>
        <p className="m-0 text-body text-text-muted">
          Le {formatDate(batch.imported_at)} à {formatTime(batch.imported_at)}.
        </p>
      </div>
      <CountList label="Rapport de l'import">
        <CountLine tone="success">
          {`${linesText(batch.rows_imported)} importée${batch.rows_imported > 1 ? "s" : ""}`}
        </CountLine>
        {batch.rows_ignored > 0 && (
          <CountLine tone="danger">
            {`${linesText(batch.rows_ignored)} ignorée${batch.rows_ignored > 1 ? "s" : ""}`}
          </CountLine>
        )}
        {batch.created.map((created) => (
          <CountLine key={created.entity} tone="muted">
            {createdText(created.entity, created.count)}
          </CountLine>
        ))}
      </CountList>
      <Button variant="secondary" icon={FileSpreadsheet} onClick={onAgain}>
        {AGAIN_LABEL}
      </Button>
    </>
  );
}
