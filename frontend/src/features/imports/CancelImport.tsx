import { useState } from "react";
import { Undo2 } from "lucide-react";
import type { ImportBatch } from "../../core/gateways/importsContract";
import { useImports } from "../../core/gateways/httpImports";
import { Button, ConfirmDialog } from "../../shared/ui";
import { asError } from "../expenses/useLoad";
import { cancelFailure, type CancelFailure } from "./cancelErrors";

export const CANCEL_LABEL = "Annuler l'import";
export const CANCEL_EFFECT = "Rien n'est effacé : les éléments sont archivés.";
export const CANCELLED = "Import annulé : les éléments sont archivés.";

/** Issue d'une annulation : message à montrer, et faut-il relire le lot. */
export type CancelOutcome = CancelFailure & { tone: "success" | "danger" };

export interface CancelImportProps {
  shopId: string;
  batch: ImportBatch;
  onOutcome: (outcome: CancelOutcome | null) => void;
}

/**
 * « Annuler l'import » (propriétaire, dans les 7 jours, UC-IMP-03) : confirmation qui dit
 * l'effet ; l'issue (annulé, opérations qui bloquent, délai dépassé, déjà annulé) remonte au
 * détail, qui l'affiche même si le bouton disparaît. Erreur imprévue : relancée.
 */
export function CancelImport({ shopId, batch, onOutcome }: CancelImportProps) {
  const gateway = useImports();
  const [asking, setAsking] = useState(false);
  const [busy, setBusy] = useState(false);
  const [fatal, setFatal] = useState<unknown>(null);
  if (fatal !== null) throw asError(fatal);

  const confirm = async () => {
    setAsking(false);
    setBusy(true);
    onOutcome(null);
    try {
      await gateway.cancel(shopId, batch.id);
      onOutcome({ tone: "success", text: CANCELLED, blocking: [], refresh: true });
    } catch (error) {
      try {
        onOutcome({ tone: "danger", ...cancelFailure(error, batch) });
      } catch (unexpected) {
        setFatal(unexpected);
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <Button
        variant="danger"
        icon={Undo2}
        loading={busy}
        onClick={() => {
          setAsking(true);
        }}
      >
        {CANCEL_LABEL}
      </Button>
      <ConfirmDialog
        open={asking}
        title={`Annuler l'import ${batch.number} ?`}
        confirmLabel={CANCEL_LABEL}
        confirmIcon={Undo2}
        onConfirm={() => {
          void confirm();
        }}
        onCancel={() => {
          setAsking(false);
        }}
      >
        {CANCEL_EFFECT}
      </ConfirmDialog>
    </>
  );
}
