import { useState } from "react";
import { ArrowLeft, RefreshCw } from "lucide-react";
import type { ImportBatch } from "../../core/gateways/importsContract";
import { useImports } from "../../core/gateways/httpImports";
import { Banner, Button, Skeleton } from "../../shared/ui";
import { useLoad } from "../expenses/useLoad";
import { BatchDetail } from "./BatchDetail";
import type { CancelOutcome } from "./CancelImport";
import { OutcomeMessage } from "./OutcomeMessage";
import { BatchList, HISTORY_LABEL } from "./BatchList";
import type { SaveFile } from "./saveFile";

export const BACK_TO_LIST = "Retour aux imports passés";

export interface ImportHistoryProps {
  shopId: string;
  /** Jour métier à Douala (« AAAA-MM-JJ ») : borne du délai d'annulation. */
  today: string;
  canCancel: boolean;
  save: SaveFile;
}

/** « Imports passés » (T45) : liste des lots, puis détail du lot ouvert. */
export function ImportHistory({ shopId, today, canCancel, save }: ImportHistoryProps) {
  const [open, setOpen] = useState<ImportBatch | null>(null);
  if (open === null) {
    return (
      <>
        <h1 className="m-0 text-title font-bold text-text">{HISTORY_LABEL}</h1>
        <BatchList shopId={shopId} today={today} onOpen={setOpen} />
      </>
    );
  }
  return (
    <>
      <Button
        variant="ghost"
        icon={ArrowLeft}
        onClick={() => {
          setOpen(null);
        }}
      >
        {BACK_TO_LIST}
      </Button>
      <h1 className="m-0 text-title font-bold text-text">Import {open.number}</h1>
      <LoadedDetail
        shopId={shopId}
        batchId={open.id}
        today={today}
        canCancel={canCancel}
        save={save}
      />
    </>
  );
}

type LoadedDetailProps = ImportHistoryProps & { batchId: string };

function LoadedDetail({ shopId, batchId, today, canCancel, save }: LoadedDetailProps) {
  const gateway = useImports();
  const [version, setVersion] = useState(0);
  const [outcome, setOutcome] = useState<CancelOutcome | null>(null);
  const reload = () => {
    setVersion((n) => n + 1);
  };
  const onOutcome = (next: CancelOutcome | null) => {
    setOutcome(next);
    if (next?.refresh === true) reload();
  };
  const loaded = useLoad(`${batchId}:${String(version)}`, () => gateway.detail(shopId, batchId));
  return (
    <>
      {loaded.status === "loading" && <Skeleton lines={4} label="Chargement du lot…" />}
      {loaded.status === "offline" && (
        <Banner
          title="Connexion nécessaire pour voir ce lot."
          action={
            <Button variant="secondary" icon={RefreshCw} onClick={reload}>
              Réessayer
            </Button>
          }
        />
      )}
      {loaded.status === "ready" && (
        <BatchDetail
          shopId={shopId}
          batch={loaded.value}
          today={today}
          canCancel={canCancel}
          save={save}
          onOutcome={onOutcome}
        />
      )}
      <div aria-live="polite">{outcome !== null && <OutcomeMessage outcome={outcome} />}</div>
    </>
  );
}
